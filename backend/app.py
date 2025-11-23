import base64
import os
import shutil
import subprocess
import sys
import textwrap
import time
import uuid
from typing import List

import imageio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

from backend.vector_store.chroma_store import ChromaDB
from backend.agents.test_case_agent import TestGenerationAgent
from backend.agents.selenium_agent import SeleniumAgent
from backend.agents.ingestion_agent import IngestionAgent
from backend.utils.script_validation import SeleniumScriptValidator, ScriptValidationError

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
    video_b64 = None
    if os.path.exists(video_path):
        with open(video_path, "rb") as video_file:
            video_b64 = base64.b64encode(video_file.read()).decode("ascii")

    gif_path = os.path.join(run_dir, "playback.gif")
    gif_b64 = None
    try:
        built_gif = _build_gif_from_frames(live_dir, gif_path)
        if built_gif and os.path.exists(built_gif):
            with open(built_gif, "rb") as gif_file:
                gif_b64 = base64.b64encode(gif_file.read()).decode("ascii")
    except Exception:
        gif_b64 = None

    return {
        "run_id": run_id,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "mp4_base64": video_b64,
        "gif_base64": gif_b64,
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


def _build_gif_from_frames(frame_dir: str, output_path: str, fps: int = 4) -> str | None:
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

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
