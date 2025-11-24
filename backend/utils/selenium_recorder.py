import atexit
import hashlib
import json
import os
import shutil
import threading
import time
from io import BytesIO
from typing import Optional

from PIL import Image


class RecordingManager:
    _patched = False
    _driver = None
    _capture_thread: Optional[threading.Thread] = None
    _running = False
    _fps = 16
    _interval = 0.25
    _live_dir: Optional[str] = None
    _segments_path: Optional[str] = None
    _last_sig: Optional[str] = None
    _lock = threading.Lock()
    _active_sessions = 0
    _frame_counter = 0
    _atexit_registered = False
    _case_labels: list[str] = []
    _segments: list[dict] = []

    @classmethod
    def configure(cls, output_dir: str, fps: int = 8, interval: float = 0.25):
        os.makedirs(output_dir, exist_ok=True)
        cls._live_dir = os.path.join(output_dir, "live_frames")
        if os.path.exists(cls._live_dir):
            shutil.rmtree(cls._live_dir, ignore_errors=True)
        os.makedirs(cls._live_dir, exist_ok=True)
        cls._segments_path = os.path.join(output_dir, "segments.json")
        cls._fps = max(1, fps)
        cls._interval = max(0.05, interval)
        cls._last_sig = None
        cls._frame_counter = 0
        cls._active_sessions = 0
        cls._running = False
        cls._capture_thread = None
        cls._case_labels = []
        cls._segments = []
        cls._patch_webdriver()
        if not cls._atexit_registered:
            atexit.register(cls.shutdown)
            cls._atexit_registered = True

    @classmethod
    def set_case_labels(cls, labels):
        with cls._lock:
            cls._case_labels = list(labels or [])

    @classmethod
    def _patch_webdriver(cls):
        if cls._patched:
            return
        from selenium import webdriver as selenium_webdriver

        original_chrome = selenium_webdriver.Chrome

        class RecordingChrome(original_chrome):  # type: ignore[misc]
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                RecordingManager.attach(self)

            def quit(self):  # type: ignore[override]
                RecordingManager.detach()
                return super().quit()

        selenium_webdriver.Chrome = RecordingChrome  # type: ignore[assignment]
        cls._patched = True

    @classmethod
    def attach(cls, driver):
        with cls._lock:
            cls._driver = driver
            cls._active_sessions += 1
            cls._last_sig = None
            if cls._live_dir:
                done_flag = os.path.join(cls._live_dir, "_done")
                if os.path.exists(done_flag):
                    try:
                        os.remove(done_flag)
                    except OSError:
                        pass
            cls._begin_segment_locked()
            if not cls._capture_thread or not cls._capture_thread.is_alive():
                cls._running = True
                cls._capture_thread = threading.Thread(target=cls._capture_loop, daemon=True)
                cls._capture_thread.start()

    @classmethod
    def detach(cls):
        with cls._lock:
            cls._active_sessions = max(0, cls._active_sessions - 1)
            if cls._active_sessions == 0:
                cls._driver = None
                cls._last_sig = None
                cls._close_segment_locked()

    @classmethod
    def _capture_loop(cls):
        while cls._running:
            driver = cls._driver
            if not driver:
                time.sleep(cls._interval)
                continue
            try:
                chunk = driver.get_screenshot_as_png()
            except Exception:
                time.sleep(cls._interval)
                continue
            cls._ingest_chunk(chunk)
            time.sleep(cls._interval)

    @classmethod
    def _ingest_chunk(cls, chunk: bytes):
        try:
            image = Image.open(BytesIO(chunk)).convert("RGB")
        except Exception:
            return
        try:
            sig = hashlib.sha1(image.tobytes()).hexdigest()
        except Exception:
            image.close()
            return
        if sig == cls._last_sig:
            image.close()
            return
        cls._last_sig = sig
        # resize long dimension to max 1280 to limit writer load (adjustable)
        max_dim = 1280
        w, h = image.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            new_size = (int(w * scale), int(h * scale))
            image = image.resize(new_size, Image.BILINEAR)
        out = BytesIO()
        try:
            image.save(out, format="JPEG", quality=75)
            frame_bytes = out.getvalue()
        finally:
            out.close()
            image.close()
        cls._write_frame(frame_bytes)

    @classmethod
    def _write_frame(cls, frame_bytes: bytes):
        try:
            img = Image.open(BytesIO(frame_bytes)).convert("RGB")
            cls._frame_counter += 1
            if cls._live_dir:
                try:
                    frame_name = f"frame_{cls._frame_counter:06d}.jpg"
                    img.save(os.path.join(cls._live_dir, frame_name), "JPEG", quality=80)
                except Exception:
                    pass
            img.close()
        except Exception:
            pass

    @classmethod
    def shutdown(cls):
        with cls._lock:
            cls._running = False
            cls._driver = None
            cls._active_sessions = 0
            cls._close_segment_locked()
        if cls._capture_thread and cls._capture_thread.is_alive():
            cls._capture_thread.join(timeout=3)
        cls._capture_thread = None
        cls._mark_done()

    @classmethod
    def _mark_done(cls):
        if not cls._live_dir:
            return
        cls._persist_segments()
        try:
            with open(os.path.join(cls._live_dir, "_done"), "w", encoding="utf-8") as fh:
                fh.write("done")
        except Exception:
            pass

    @classmethod
    def _begin_segment_locked(cls):
        start = cls._frame_counter + 1
        label = None
        if len(cls._segments) < len(cls._case_labels):
            label = cls._case_labels[len(cls._segments)]
        else:
            label = f"Case {len(cls._segments) + 1}"
        cls._segments.append({"label": label, "start_frame": start, "end_frame": None})

    @classmethod
    def _close_segment_locked(cls):
        if not cls._segments:
            return
        current = cls._segments[-1]
        if current.get("end_frame") is not None:
            return
        current["end_frame"] = cls._frame_counter

    @classmethod
    def _persist_segments(cls):
        if not cls._segments_path:
            return
        packed = []
        for seg in cls._segments:
            if seg.get("start_frame") is None:
                continue
            end_frame = seg.get("end_frame") if seg.get("end_frame") is not None else cls._frame_counter
            packed.append({
                "label": seg.get("label") or "Case",
                "start_frame": seg["start_frame"],
                "end_frame": end_frame,
            })
        try:
            with open(cls._segments_path, "w", encoding="utf-8") as fh:
                json.dump(packed, fh)
        except Exception:
            pass
