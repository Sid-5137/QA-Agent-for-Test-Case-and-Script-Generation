import atexit
import hashlib
import os
import queue
import shutil
import threading
import time
from io import BytesIO
from typing import Optional

import imageio
import numpy as np
from PIL import Image

class RecordingManager:
    _patched = False
    _driver = None
    _worker: Optional[threading.Thread] = None
    _capture_thread: Optional[threading.Thread] = None
    _running = False
    _fps = 8
    _interval = 0.25
    _live_dir: Optional[str] = None
    _video_path: Optional[str] = None
    _frame_q: "queue.Queue[bytes]" = queue.Queue(maxsize=256)
    _last_sig: Optional[str] = None
    _video_writer = None
    _lock = threading.Lock()
    _active_sessions = 0
    _live_frame_every = 4
    _frame_counter = 0
    _writer_kwargs = dict(format="FFMPEG", codec="libx264", quality=8, pixelformat="yuv420p")

    @classmethod
    def configure(cls, output_dir: str, fps: int = 8, interval: float = 0.25, live_frame_every: int = 4):
        os.makedirs(output_dir, exist_ok=True)
        cls._video_path = os.path.join(output_dir, "playback.mp4")
        cls._live_dir = os.path.join(output_dir, "live_frames")
        if os.path.exists(cls._live_dir):
            shutil.rmtree(cls._live_dir, ignore_errors=True)
        os.makedirs(cls._live_dir, exist_ok=True)
        cls._fps = max(1, fps)
        cls._interval = max(0.05, interval)
        cls._live_frame_every = max(1, live_frame_every)
        cls._frame_q = queue.Queue(maxsize=512)
        cls._last_sig = None
        cls._frame_counter = 0
        cls._active_sessions = 0
        cls._running = False
        cls._video_writer = None
        cls._start_worker()
        cls._patch_webdriver()
        atexit.register(cls.detach)

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
    def _start_worker(cls):
        if cls._worker and cls._worker.is_alive():
            return
        cls._running = True
        cls._worker = threading.Thread(target=cls._writer_loop, daemon=True)
        cls._worker.start()

    @classmethod
    def attach(cls, driver):
        with cls._lock:
            cls._driver = driver
            cls._active_sessions += 1
            if not cls._capture_thread or not cls._capture_thread.is_alive():
                cls._capture_thread = threading.Thread(target=cls._capture_loop, daemon=True)
                cls._capture_thread.start()

    @classmethod
    def detach(cls):
        with cls._lock:
            cls._active_sessions = max(0, cls._active_sessions - 1)
            if cls._active_sessions == 0:
                cls._running = False
                # flush queue and close writer
                if cls._worker and cls._worker.is_alive():
                    cls._worker.join(timeout=3)
                cls._close_writer()
                cls._mark_done()
                cls._driver = None

    @classmethod
    def _capture_loop(cls):
        while cls._active_sessions > 0:
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
        try:
            cls._frame_q.put_nowait(frame_bytes)
        except queue.Full:
            # drop oldest to keep queue moving
            try:
                _ = cls._frame_q.get_nowait()
                cls._frame_q.put_nowait(frame_bytes)
            except Exception:
                pass

    @classmethod
    def _writer_loop(cls):
        temp_frames = []
        last_flush = time.time()
        flush_interval = 1.0
        while cls._running or not cls._frame_q.empty():
            try:
                frame_bytes = cls._frame_q.get(timeout=0.5)
            except queue.Empty:
                frame_bytes = None
            if frame_bytes:
                temp_frames.append(frame_bytes)
            now = time.time()
            if temp_frames and (len(temp_frames) >= 5 or (now - last_flush) >= flush_interval):
                cls._write_frames_batch(temp_frames)
                temp_frames = []
                last_flush = now
        # final flush
        if temp_frames:
            cls._write_frames_batch(temp_frames)
        cls._close_writer()

    @classmethod
    def _write_frames_batch(cls, frames: "list[bytes]"):
        if not frames:
            return
        if cls._video_writer is None:
            try:
                cls._video_writer = imageio.get_writer(cls._video_path, fps=cls._fps, **cls._writer_kwargs)
            except Exception:
                cls._video_writer = None
                return
        for fb in frames:
            try:
                img = Image.open(BytesIO(fb)).convert("RGB")
                arr = np.array(img)
                h, w, _ = arr.shape
                pad_h = h % 2
                pad_w = w % 2
                if pad_h or pad_w:
                    arr = np.pad(arr, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
                cls._video_writer.append_data(arr)
                # write live frame every N frames
                cls._frame_counter += 1
                if cls._frame_counter % cls._live_frame_every == 0 and cls._live_dir:
                    try:
                        png_path = os.path.join(cls._live_dir, f"frame_{cls._frame_counter:06d}.jpg")
                        img.save(png_path, "JPEG", quality=80)
                    except Exception:
                        pass
                img.close()
            except Exception:
                continue

    @classmethod
    def _close_writer(cls):
        if cls._video_writer:
            try:
                cls._video_writer.close()
            except Exception:
                pass
            finally:
                cls._video_writer = None

    @classmethod
    def _mark_done(cls):
        if not cls._live_dir:
            return
        try:
            with open(os.path.join(cls._live_dir, "_done"), "w", encoding="utf-8") as fh:
                fh.write("done")
        except Exception:
            pass
