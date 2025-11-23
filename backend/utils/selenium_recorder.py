import atexit
import hashlib
import os
import shutil
import threading
import time
from io import BytesIO
from typing import Optional

import imageio
import numpy as np
from PIL import Image

class RecordingManager:

    _patched: bool = False
    _driver = None
    _thread: Optional[threading.Thread] = None
    _running: bool = False
    _fps: int = 14
    _interval: float = 0.5
    _live_dir: Optional[str] = None
    _frame_counter: int = 0
    _last_signature: Optional[str] = None
    _video_path: Optional[str] = None
    _video_writer = None
    _active_sessions: int = 0

    @classmethod
    def configure(cls, output_dir: str, run_id: str | None = None, fps: int = 4, interval: float = 0.5) -> None:
        os.makedirs(output_dir, exist_ok=True)
        cls._video_path = os.path.join(output_dir, "playback.mp4")
        cls._fps = fps
        cls._interval = interval
        cls._driver = None
        cls._running = False
        cls._thread = None
        cls._video_writer = None
        cls._live_dir = os.path.join(output_dir, "live_frames")
        cls._frame_counter = 0
        cls._last_signature = None
        cls._active_sessions = 0

        if cls._live_dir:
            if os.path.exists(cls._live_dir):
                shutil.rmtree(cls._live_dir, ignore_errors=True)
            os.makedirs(cls._live_dir, exist_ok=True)
            done_flag = os.path.join(cls._live_dir, "_done")
            if os.path.exists(done_flag):
                os.remove(done_flag)

        cls._patch_webdriver()
        atexit.register(cls.detach)

    @classmethod
    def _patch_webdriver(cls) -> None:
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
    def attach(cls, driver) -> None:
        cls._driver = driver
        cls._running = True
        cls._active_sessions += 1
        cls._clear_done_flag()
        cls._thread = threading.Thread(target=cls._capture_loop, daemon=True)
        cls._thread.start()

    @classmethod
    def detach(cls) -> None:
        if not cls._driver:
            return
        cls._running = False
        if cls._thread and cls._thread.is_alive():
            cls._thread.join(timeout=3)
        cls._active_sessions = max(0, cls._active_sessions - 1)
        if cls._active_sessions == 0:
            cls._close_writer()
            cls._mark_stream_complete()
        cls._driver = None
        cls._thread = None
        cls._last_signature = None

    @classmethod
    def _capture_loop(cls) -> None:
        while cls._running and cls._driver:
            try:
                frame = cls._driver.get_screenshot_as_png()
                cls._ingest_frame(frame)
            except Exception:
                pass
            time.sleep(cls._interval)

    @classmethod
    def _ingest_frame(cls, chunk: bytes) -> None:
        try:
            image = Image.open(BytesIO(chunk)).convert("RGB")
        except Exception:
            return

        signature = hashlib.sha1(image.tobytes()).hexdigest()
        if signature == cls._last_signature:
            image.close()
            return

        cls._last_signature = signature
        cls._append_video_frame(image)
        cls._write_live_frame(image)
        image.close()

    @classmethod
    def _append_video_frame(cls, image: Image.Image) -> None:
        if not cls._video_path:
            return
        if cls._video_writer is None:
            fps = max(cls._fps, 1)
            try:
                cls._video_writer = imageio.get_writer(
                    cls._video_path,
                    format="FFMPEG",
                    mode="I",
                    fps=fps,
                    codec="libx264",
                    quality=8,
                    macro_block_size=1,
                    pixelformat="yuv420p",
                )
            except Exception:
                cls._video_writer = None
                return
        try:
            frame_array = np.array(image)
            h, w, _ = frame_array.shape
            pad_h = h % 2
            pad_w = w % 2
            if pad_h or pad_w:
                frame_array = np.pad(frame_array, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
            cls._video_writer.append_data(frame_array)
        except Exception:
            pass

    @classmethod
    def _write_live_frame(cls, image: Image.Image) -> None:
        if not cls._live_dir:
            return
        path = os.path.join(cls._live_dir, f"frame_{cls._frame_counter:05d}.jpg")
        cls._frame_counter += 1
        try:
            image.save(path, "JPEG", quality=85)
        except Exception:
            pass

    @classmethod
    def _close_writer(cls) -> None:
        if not cls._video_writer:
            return
        try:
            cls._video_writer.close()
        except Exception:
            pass
        finally:
            cls._video_writer = None

    @classmethod
    def _mark_stream_complete(cls) -> None:
        if not cls._live_dir:
            return
        done_flag = os.path.join(cls._live_dir, "_done")
        try:
            with open(done_flag, "w", encoding="utf-8") as marker:
                marker.write("done")
        except OSError:
            pass

    @classmethod
    def _clear_done_flag(cls) -> None:
        if not cls._live_dir:
            return
        done_flag = os.path.join(cls._live_dir, "_done")
        if os.path.exists(done_flag):
            try:
                os.remove(done_flag)
            except OSError:
                pass