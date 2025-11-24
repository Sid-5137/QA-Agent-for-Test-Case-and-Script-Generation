import base64
import json
import re
import os
import shutil
import subprocess
import sys
import textwrap
import time
import uuid
from io import BytesIO
from typing import List

import imageio
import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

from backend.vector_store.chroma_store import ChromaDB
from backend.agents.test_case_agent import TestGenerationAgent
from backend.agents.selenium_agent import SeleniumAgent
from backend.agents.ingestion_agent import IngestionAgent
from backend.utils.script_validation import SeleniumScriptValidator, ScriptValidationError

PLAYBACK_FPS = 2

app = FastAPI(title="QA Agent Backend")

UPLOAD_DIR = os.path.abspath("uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ingestion_agent = IngestionAgent()
test_agent = TestGenerationAgent()
selenium_agent = SeleniumAgent()

class UploadResponse(BaseModel):
    status: str
    docs_path: str
    files: List[str]


class BuildKBRequest(BaseModel):
    docs_path: str


class GenerateTestsRequest(BaseModel):
    docs_path: str
    query: str
    rebuild: bool = False


class TestCasePayload(BaseModel):
    id: str
    feature: str
    scenario: str
    expected_result: str
    grounded_in: List[str] = Field(default_factory=list)
    raw_block: str | None = None


class SeleniumRequest(BaseModel):
    docs_path: str
    query: str
    html: str
    selected_ids: List[str]
    test_cases: List[TestCasePayload]


class ValidateScriptRequest(BaseModel):
    docs_path: str
    script: str
    html: str


class RunSeleniumRequest(BaseModel):
    docs_path: str
    script: str
    html: str
    run_id: str | None = None
    selected_ids: List[str] | None = None


def _sanitize_script(script: str) -> str:
    text = (script or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        fenced: List[str] = []
        for line in lines:
            if line.strip().startswith("```"):
                break
            fenced.append(line)
        if fenced:
            lines = fenced
        text = "\n".join(lines).strip()
    if text.lower().startswith("python"):
        lines = text.splitlines()
        if lines and lines[0].strip().lower() == "python":
            text = "\n".join(lines[1:]).strip()
    return text

def _ensure_vector_store(docs_path: str, force: bool = False):
    vector_path = os.path.join(docs_path, "vector_db")
    should_build = force or not os.path.exists(vector_path) or not os.listdir(vector_path)

    if should_build:
        result = ingestion_agent.ingest(docs_path)
        if result.get("status") != "success":
            raise HTTPException(status_code=400, detail=result.get("message", "Ingestion failed"))
        return result

    return {"status": "success", "message": "Vector store already available", "vector_db_path": vector_path}


@app.post("/build_kb")
def build_kb(req: BuildKBRequest):
    if not os.path.exists(req.docs_path):
        raise HTTPException(status_code=400, detail="docs_path does not exist")

    result = ingestion_agent.ingest(req.docs_path)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message", "Ingestion failed"))

    return result

@app.post("/upload_files", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    dest = os.path.join(UPLOAD_DIR, f"batch_{os.getpid()}")
    os.makedirs(dest, exist_ok=True)

    saved = []
    for f in files:
        path = os.path.join(dest, f.filename)
        with open(path, "wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(path)

    return {"status": "ok", "docs_path": dest, "files": saved}


@app.post("/generate_tests")
def generate_tests(req: GenerateTestsRequest):

    if not os.path.exists(req.docs_path):
        raise HTTPException(status_code=400, detail="docs_path does not exist")

    ingestion_result = _ensure_vector_store(req.docs_path, force=req.rebuild)

    try:
        result = test_agent.generate(docs_path=req.docs_path, query=req.query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "ok",
        "test_cases": result.get("test_cases", []),
        "raw_response": result.get("raw_response", ""),
        "ingestion_result": ingestion_result,
    }


@app.post("/generate_selenium")
def generate_selenium(req: SeleniumRequest):

    if not os.path.exists(req.docs_path):
        raise HTTPException(status_code=400, detail="docs_path does not exist")

    _ensure_vector_store(req.docs_path, force=False)

    vector_path = os.path.join(req.docs_path, "vector_db")
    db = ChromaDB(persist_directory=vector_path)
    docs = db.similarity_search(req.query, k=5)

    selected = [c for c in req.test_cases if c.id in req.selected_ids]

    if not selected:
        raise HTTPException(status_code=400, detail="No matching test cases found.")

    doc_snippets = []
    for doc in docs:
        meta = doc.get("metadata", {})
        source = meta.get("source_document") or meta.get("source") or "unknown"
        doc_snippets.append(f"[{source}]\n{doc['text']}")

    result = selenium_agent.generate(
        test_cases=[case.dict() for case in selected],
        html=req.html,
        docs="\n\n".join(doc_snippets)
    )

    return {"selenium_script": result["selenium_script"]}


@app.post("/validate_selenium")
def validate_selenium(req: ValidateScriptRequest):

    if not os.path.exists(req.docs_path):
        raise HTTPException(status_code=400, detail="docs_path does not exist")

    try:
        clean_script = _sanitize_script(req.script)
        validator = SeleniumScriptValidator(clean_script, req.html)
        report = validator.run()
    except ScriptValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return report


@app.post("/run_selenium")
def run_selenium(req: RunSeleniumRequest):

    if not os.path.exists(req.docs_path):
        raise HTTPException(status_code=400, detail="docs_path does not exist")

    requested_run_id = (req.run_id or str(uuid.uuid4())).strip()
    try:
        uuid.UUID(requested_run_id)
        run_id = requested_run_id
    except ValueError:
        run_id = str(uuid.uuid4())
    runs_root = os.path.join(req.docs_path, "runs")
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)
    live_dir = os.path.join(run_dir, "live_frames")
    os.makedirs(live_dir, exist_ok=True)

    html_path = os.path.join(run_dir, "checkout.html")
    with open(html_path, "w", encoding="utf-8") as html_file:
        html_file.write(req.html)

    clean_script = _sanitize_script(req.script)

    script_path = os.path.join(run_dir, "selenium_script.py")
    with open(script_path, "w", encoding="utf-8") as script_file:
        script_file.write(clean_script)

    run_script_path = os.path.join(run_dir, "selenium_script_run.py")
    run_dir_literal = run_dir.replace("\\", "\\\\")
    html_path_literal = html_path.replace("\\", "\\\\")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    project_root_literal = project_root.replace("\\", "\\\\")
    run_id_literal = run_id.replace("\\", "\\\\")
    prelude = textwrap.dedent(
        f"""
        import sys
        _project_root = r"{project_root_literal}"
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)
        from backend.utils.selenium_recorder import RecordingManager
        RecordingManager.configure(r"{run_dir_literal}")
        import os
        os.environ.setdefault("CHECKOUT_HTML_PATH", r"{html_path_literal}")
        _case_labels = os.environ.get("QA_AGENT_CASE_LABELS")
        if _case_labels:
            RecordingManager.set_case_labels([_lbl.strip() for _lbl in _case_labels.split("||") if _lbl.strip()])
        """
    )

    script_body = clean_script
    candidate_names = ("run", "main", "execute", "run_tests")
    has_candidate = any(f"def {name}" in script_body for name in candidate_names)
    has_main_guard = "__main__" in script_body
    needs_entrypoint = has_candidate and not has_main_guard

    with open(run_script_path, "w", encoding="utf-8") as run_script:
        run_script.write(prelude)
        run_script.write("\n")
        run_script.write(script_body)
        run_script.write("\n")
        if needs_entrypoint:
            fallback = textwrap.dedent(
                """
                if __name__ == "__main__":
                    _preferred = ["run", "main", "execute", "run_tests"]
                    _invoked = False
                    for _name in _preferred:
                        _func = globals().get(_name)
                        if callable(_func):
                            _func()
                            _invoked = True
                            break
                    if not _invoked:
                        _pattern_funcs = []
                        for _fname, _func in globals().items():
                            if not callable(_func):
                                continue
                            if _fname.startswith("run_") or _fname.startswith("test_") or _fname.startswith("case_"):
                                _pattern_funcs.append((_fname, _func))
                        if _pattern_funcs:
                            for _fname, _func in sorted(_pattern_funcs):
                                try:
                                    _func()
                                except Exception as _exc:
                                    import traceback as _tb
                                    print(f"[WARN] {_fname} failed: {_exc}")
                                    _tb.print_exc()
                            _invoked = True
                    if not _invoked:
                        raise SystemExit("No executable entrypoint found. Define run() or main().")
                """
            )
            run_script.write(fallback)

    env = os.environ.copy()
    env["CHECKOUT_HTML_PATH"] = html_path
    env.setdefault("HEADLESS", "1")
    if req.selected_ids:
        env["QA_AGENT_CASE_LABELS"] = "||".join(req.selected_ids)

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(
            [sys.executable, run_script_path],
            capture_output=True,
            text=True,
            cwd=os.path.abspath("."),
            timeout=180,
            env=env,
            creationflags=creationflags,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Selenium run timed out after 180 seconds") from exc

    video_path = os.path.join(run_dir, "playback.mp4")
    min_video_size = 8192
    rebuilt = _build_mp4_from_frames(live_dir, video_path, fps=PLAYBACK_FPS)
    video_b64 = _encode_file_base64(rebuilt or video_path, minimum_bytes=min_video_size)

    gif_path = os.path.join(run_dir, "playback.gif")
    gif_b64 = None
    try:
        built_gif = _build_gif_from_frames(live_dir, gif_path, fps=PLAYBACK_FPS)
        if built_gif and os.path.exists(built_gif):
            with open(built_gif, "rb") as gif_file:
                gif_b64 = base64.b64encode(gif_file.read()).decode("ascii")
    except Exception:
        gif_b64 = None

    segments_path = os.path.join(run_dir, "segments.json")
    case_playbacks = _build_case_playbacks(live_dir, segments_path, run_dir)

    frame_previews = _collect_frame_previews(live_dir)

    return {
        "run_id": run_id,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "mp4_base64": video_b64,
        "gif_base64": gif_b64,
        "frame_previews": frame_previews,
        "case_playbacks": case_playbacks,
        "status": "ok" if result.returncode == 0 else "error",
    }


@app.get("/live_feed")
def live_feed(docs_path: str, run_id: str):
    run_dir = os.path.join(docs_path, "runs", run_id)
    live_dir = os.path.join(run_dir, "live_frames")

    if not os.path.isdir(live_dir):
        raise HTTPException(status_code=404, detail="Live feed not initialized for this run")

    boundary = "frame"
    done_flag = os.path.join(live_dir, "_done")

    def frame_iter():
        seen = set()
        idle_cycles = 0
        while True:
            try:
                entries = sorted(f for f in os.listdir(live_dir) if f.endswith(".jpg"))
            except FileNotFoundError:
                break
            new_frames = [f for f in entries if f not in seen]

            if new_frames:
                idle_cycles = 0
                for name in new_frames:
                    path = os.path.join(live_dir, name)
                    try:
                        with open(path, "rb") as frame_file:
                            data = frame_file.read()
                    except FileNotFoundError:
                        continue
                    seen.add(name)
                    yield (
                        f"--{boundary}\r\n".encode("ascii")
                        + b"Content-Type: image/jpeg\r\n\r\n"
                        + data
                        + b"\r\n"
                    )
            else:
                idle_cycles += 1
                if os.path.exists(done_flag) and idle_cycles > 10:
                    break
                time.sleep(0.1)

        yield f"--{boundary}--\r\n".encode("ascii")

    return StreamingResponse(frame_iter(), media_type=f"multipart/x-mixed-replace; boundary={boundary}")


def _build_gif_from_frames(frame_dir: str, output_path: str, fps: int = PLAYBACK_FPS) -> str | None:
    if not os.path.isdir(frame_dir):
        return None
    frame_files = sorted(f for f in os.listdir(frame_dir) if f.endswith(".jpg"))
    if not frame_files:
        return None

    frames = []
    for name in frame_files:
        path = os.path.join(frame_dir, name)
        try:
            frames.append(imageio.imread(path))
        except Exception:
            continue

    if not frames:
        return None

    duration = max(0.05, 1.0 / max(fps, 1))
    imageio.mimsave(output_path, frames, format="GIF", duration=duration)
    return output_path


def _build_mp4_from_frames(
    frame_dir: str,
    output_path: str,
    fps: int = PLAYBACK_FPS,
    frame_subset: list[str] | None = None,
) -> str | None:
    if not os.path.isdir(frame_dir):
        return None
    if frame_subset is not None:
        frame_files = list(frame_subset)
    else:
        frame_files = sorted(f for f in os.listdir(frame_dir) if f.endswith(".jpg"))
    if not frame_files:
        return None

    try:
        if os.path.exists(output_path):
            os.remove(output_path)
    except Exception:
        pass

    writer = None
    try:
        writer = imageio.get_writer(
            output_path,
            fps=fps,
            format="FFMPEG",
            codec="libx264",
            quality=8,
            pixelformat="yuv420p",
            macro_block_size=1,
        )
        for name in frame_files:
            path = os.path.join(frame_dir, name)
            try:
                frame = imageio.imread(path)
            except Exception:
                continue
            h, w = frame.shape[:2]
            pad_h = h % 2
            pad_w = w % 2
            if pad_h or pad_w:
                frame = np.pad(frame, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
            writer.append_data(frame)
        writer.close()
        return output_path
    except Exception:
        if writer:
            try:
                writer.close()
            except Exception:
                pass

    try:
        frames = []
        for name in frame_files:
            path = os.path.join(frame_dir, name)
            try:
                frames.append(imageio.imread(path))
            except Exception:
                continue
        if frames:
            imageio.mimsave(output_path, frames, format="MP4", fps=fps)
            return output_path
    except Exception:
        return None

    return output_path if os.path.exists(output_path) else None


def _collect_frame_previews(frame_dir: str, total: int = 3, max_width: int = 720) -> list[str]:
    if not os.path.isdir(frame_dir):
        return []
    frame_files = sorted(f for f in os.listdir(frame_dir) if f.endswith(".jpg"))
    if not frame_files:
        return []

    indices = []
    if len(frame_files) <= total:
        indices = list(range(len(frame_files)))
    else:
        step = max(1, len(frame_files) // (total - 1)) if total > 1 else len(frame_files)
        indices = [0]
        cursor = step
        while len(indices) < total - 1 and cursor < len(frame_files) - 1:
            indices.append(cursor)
            cursor += step
        indices.append(len(frame_files) - 1)

    previews: list[str] = []
    for idx in indices:
        name = frame_files[idx]
        path = os.path.join(frame_dir, name)
        try:
            image = Image.open(path).convert("RGB")
            image.thumbnail((max_width, max_width))
            out = BytesIO()
            image.save(out, format="JPEG", quality=85)
            previews.append(base64.b64encode(out.getvalue()).decode("ascii"))
            out.close()
            image.close()
        except Exception:
            continue
    return previews


def _encode_file_base64(path: str | None, minimum_bytes: int = 1) -> str | None:
    if not path or not os.path.isfile(path):
        return None
    try:
        size = os.path.getsize(path)
    except OSError:
        return None
    if size < max(minimum_bytes, 1):
        return None
    try:
        with open(path, "rb") as fh:
            return base64.b64encode(fh.read()).decode("ascii")
    except Exception:
        return None


def _load_segments(path: str) -> list[dict]:
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []


def _frame_number_from_name(name: str) -> int | None:
    if not name or "frame_" not in name:
        return None
    stem = name.split("frame_")[-1]
    stem = stem.split(".")[0]
    try:
        return int(stem)
    except ValueError:
        return None


def _subset_frames(all_frames: list[str], start_frame: int, end_frame: int) -> list[str]:
    if not all_frames or start_frame <= 0 or end_frame < start_frame:
        return []
    subset: list[str] = []
    for name in all_frames:
        idx = _frame_number_from_name(name)
        if idx is None:
            continue
        if idx < start_frame:
            continue
        if idx > end_frame:
            break
        subset.append(name)
    return subset


def _slugify_label(value: str) -> str:
    if not value:
        return "case"
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "case"


def _build_case_playbacks(frame_dir: str, segments_path: str, run_dir: str) -> list[dict]:
    segments = _load_segments(segments_path)
    if not segments:
        return []
    all_frames = sorted(f for f in os.listdir(frame_dir) if f.endswith(".jpg")) if os.path.isdir(frame_dir) else []
    if not all_frames:
        return []
    playbacks: list[dict] = []
    for idx, seg in enumerate(segments):
        start = int(seg.get("start_frame") or 0)
        end = int(seg.get("end_frame") or 0)
        if start <= 0 or end < start:
            continue
        frame_subset = _subset_frames(all_frames, start, end)
        if not frame_subset:
            continue
        label = seg.get("label") or f"Case {idx + 1}"
        safe_label = _slugify_label(label)
        output_path = os.path.join(run_dir, f"{safe_label}_playback.mp4")
        built = _build_mp4_from_frames(frame_dir, output_path, fps=PLAYBACK_FPS, frame_subset=frame_subset)
        media_b64 = _encode_file_base64(built, minimum_bytes=2048)
        if not media_b64:
            continue
        playbacks.append({
            "label": label,
            "start_frame": start,
            "end_frame": end,
            "mp4_base64": media_b64,
        })
    return playbacks

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
