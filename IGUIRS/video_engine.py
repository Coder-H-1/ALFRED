"""
IGUIRS Video Engine & Dynamic Window Player
-------------------------------------------
Handles yt-dlp search/resolution, interactive user option selector,
background stream buffer fetching, borderless 800x600 Tkinter player window,
and garbage collection on stream termination.
"""

import os
import sys
import gc
import time
import queue
import psutil
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from PIL import Image, ImageTk
import cv2

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from FILES.logger import get_logger
    logger = get_logger("IGUIRS.VideoEngine")
    player_logger = get_logger("IGUIRS.VideoPlayer")
    lifecycle_logger = get_logger("IGUIRS.Lifecycle")
except Exception:
    import logging
    logger = logging.getLogger("IGUIRS.VideoEngine")
    player_logger = logging.getLogger("IGUIRS.VideoPlayer")
    lifecycle_logger = logging.getLogger("IGUIRS.Lifecycle")


def format_duration(seconds):
    if not seconds:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def search_video_options(query_or_url: str, max_results: int = 5) -> list:
    """
    Provide user with video options instead of playing the first one.
    """
    import yt_dlp

    logger.info(f"Resolving options for query/url: '{query_or_url}' (max {max_results})")
    
    # Direct single video link check
    is_direct_url = any(domain in query_or_url for domain in ("youtube.com/watch", "youtu.be/", "vimeo.com"))
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist" if not is_direct_url else False,
        "skip_download": True,
    }

    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if is_direct_url:
                info = ydl.extract_info(query_or_url, download=False)
                results.append({
                    "title": info.get("title", "Unknown Title"),
                    "url": info.get("webpage_url", query_or_url),
                    "duration": format_duration(info.get("duration")),
                    "uploader": info.get("uploader", "Unknown"),
                    "id": info.get("id", ""),
                })
            else:
                search_query = f"ytsearch{max_results}:{query_or_url}"
                search_results = ydl.extract_info(search_query, download=False)
                entries = search_results.get("entries", [])
                for entry in entries:
                    if not entry:
                        continue
                    results.append({
                        "title": entry.get("title", "Unknown Title"),
                        "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                        "duration": format_duration(entry.get("duration")),
                        "uploader": entry.get("uploader") or entry.get("channel", "Unknown"),
                        "id": entry.get("id", ""),
                    })
    except Exception as e:
        logger.error(f"Error fetching video options with yt-dlp: {e}")
        # Fallback raw entry
        results.append({
            "title": query_or_url,
            "url": query_or_url,
            "duration": "--:--",
            "uploader": "Direct Input",
            "id": ""
        })

    logger.info(f"Found {len(results)} option(s) for '{query_or_url}'")
    return results


def resolve_stream_source(video_url: str, max_height: int = 480) -> dict:
    """
    Extract direct stream buffer URL and metadata.
    Prioritizes low-resolution video (<=480p) to eliminate frame lag and minimize buffer overhead.
    """
    import yt_dlp

    logger.info(f"Extracting low-latency stream URL (target max {max_height}p) for: {video_url}")
    ydl_opts = {
        "format": f"bestvideo[height<={max_height}][ext=mp4]/bestvideo[height<={max_height}]/bestvideo[height<=720]/best[height<={max_height}]/best/worst",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        stream_url = info.get("url")
        fps = info.get("fps") or 30
        width = info.get("width") or 800
        height = info.get("height") or 600
        title = info.get("title", "Video")

    # Extract audio stream
    audio_url = None
    try:
        audio_opts = {
            "format": "ba[ext=m4a]/bestaudio[ext=m4a]/ba/best",
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(audio_opts) as a_ydl:
            a_info = a_ydl.extract_info(video_url, download=False)
            audio_url = a_info.get("url")
            logger.info(f"Audio stream extracted: format={a_info.get('format_id')}, acodec={a_info.get('acodec')}")
    except Exception as e:
        logger.warning(f"Audio extraction fallback: {e}")

    logger.info(f"Stream resolved: title='{title}', fps={fps}, resolution={width}x{height}, has_audio={audio_url is not None}")
    return {
        "stream_url": stream_url,
        "audio_url": audio_url,
        "fps": fps,
        "width": width,
        "height": height,
        "title": title
    }


class VideoSelectorModal(tk.Toplevel):
    """
    HUD Dialog allowing user to select a video option by number or click.
    """
    def __init__(self, master, query: str, options: list, on_selected):
        super().__init__(master)
        self.on_selected = on_selected
        self.options = options
        self.selected_index = None

        self.title("Select Video")
        self.configure(bg="#0f1115")
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Center on screen
        w, h = 680, min(550, 120 + len(options) * 65)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Dragging
        self._drag_x = 0
        self._drag_y = 0
        self.bind("<Button-1>", self._start_drag)
        self.bind("<B1-Motion>", self._do_drag)

        # Header
        header_frame = tk.Frame(self, bg="#1a1d24", padx=16, pady=12)
        header_frame.pack(fill=tk.X)

        title_lbl = tk.Label(
            header_frame,
            text=f"SELECT VIDEO FOR: '{query}'",
            fg="#00d4ff",
            bg="#1a1d24",
            font=("Segoe UI", 12, "bold")
        )
        title_lbl.pack(side=tk.LEFT)

        sub_lbl = tk.Label(
            header_frame,
            text="[Press 1-9 or Click | Esc to Cancel]",
            fg="#888888",
            bg="#1a1d24",
            font=("Segoe UI", 9)
        )
        sub_lbl.pack(side=tk.RIGHT)

        # Options Container
        container = tk.Frame(self, bg="#0f1115", padx=12, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        for i, opt in enumerate(options[:9]):
            idx = i + 1
            card = tk.Frame(
                container,
                bg="#161922",
                bd=1,
                relief=tk.FLAT,
                cursor="hand2",
                padx=10,
                pady=6
            )
            card.pack(fill=tk.X, pady=4)

            num_lbl = tk.Label(
                card,
                text=f"[{idx}]",
                fg="#00ffcc",
                bg="#161922",
                font=("Consolas", 11, "bold"),
                width=4
            )
            num_lbl.pack(side=tk.LEFT)

            t_text = opt["title"]
            if len(t_text) > 55:
                t_text = t_text[:52] + "..."
            t_lbl = tk.Label(
                card,
                text=t_text,
                fg="#ffffff",
                bg="#161922",
                font=("Segoe UI", 10),
                anchor="w"
            )
            t_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

            meta_text = f"{opt['duration']} | {opt['uploader'][:18]}"
            meta_lbl = tk.Label(
                card,
                text=meta_text,
                fg="#7e8590",
                bg="#161922",
                font=("Segoe UI", 9)
            )
            meta_lbl.pack(side=tk.RIGHT)

            # Bind click
            card.bind("<Button-1>", lambda e, k=i: self._select(k))
            num_lbl.bind("<Button-1>", lambda e, k=i: self._select(k))
            t_lbl.bind("<Button-1>", lambda e, k=i: self._select(k))
            meta_lbl.bind("<Button-1>", lambda e, k=i: self._select(k))

            # Bind number hotkey
            self.bind(str(idx), lambda e, k=i: self._select(k))

        self.bind("<Escape>", lambda e: self._cancel())

    def _start_drag(self, event):
        self._offset_x = event.x_root - self.winfo_x()
        self._offset_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        try:
            if not self.winfo_exists():
                return
            new_x = event.x_root - self._offset_x
            new_y = event.y_root - self._offset_y
            w = self.winfo_width()
            h = self.winfo_height()
            self.geometry(f"{w}x{h}+{new_x}+{new_y}")
        except Exception:
            pass

    def _select(self, index):
        self.selected_index = index
        logger.info(f"User selected video option [{index + 1}]: {self.options[index]['title']}")
        if self.on_selected:
            self.on_selected(self.options[index])
        self.destroy()

    def _cancel(self):
        logger.info("Video option selection cancelled by user.")
        if self.on_selected:
            self.on_selected(None)
        self.destroy()


class DynamicVideoWindow(tk.Toplevel):
    """
    Dynamic borderless video playback window (default 800x600).
    Resizable strictly via config.json args.
    Streams video frames, closes upon completion, and runs garbage collector.
    """
    def __init__(self, master, window_id: str, stream_info: dict, extra_args: list = None, on_close=None):
        super().__init__(master)
        self.window_id = window_id
        self.stream_info = stream_info
        self.extra_args = extra_args or []
        self.on_close_cb = on_close
        self.running = True

        self.title(f"IGUIRS - {stream_info.get('title', window_id)}")
        self.configure(bg="#000000")

        # Frameless window (without borders)
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Parse geometry from extra-args or use default 800x600
        self.target_w, self.target_h = self._parse_dimensions(self.extra_args)
        self._center_window(self.target_w, self.target_h)

        # Dragging support with absolute screen coordinates
        self._offset_x = 0
        self._offset_y = 0
        self.bind("<Button-1>", self._start_drag)
        self.bind("<B1-Motion>", self._do_drag)

        # Hotkeys
        self.bind("<Escape>", lambda e: self.close_window())
        self.bind("q", lambda e: self.close_window())

        # Display Canvas
        self.canvas = tk.Canvas(
            self,
            width=self.target_w,
            height=self.target_h,
            bg="#000000",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._do_drag)

        # Video stream capture handle
        self.cap = None
        self.current_frame = None
        self.photo_img = None
        self.fps = stream_info.get("fps", 30) or 30
        self.frame_delay_ms = max(10, int(1000 / self.fps))

        # Audio clock synchronization state
        self.audio_start_time = None
        self.rendered_frame_idx = 0

        # Threaded frame buffer
        self.frame_queue = queue.Queue(maxsize=30)
        self.buffer_thread = None

        # Threaded audio stream
        self.audio_thread = None
        self.audio_proc = None
        self.pa = None
        self.pa_stream = None

        player_logger.info(
            f"Initialized DynamicVideoWindow '{self.window_id}' "
            f"({self.target_w}x{self.target_h}) at {self.fps} FPS"
        )

        self._start_playback()

    def _parse_dimensions(self, extra_args: list) -> tuple:
        """Parse dimensions from extra-args. Resizable only via config."""
        w, h = 800, 600
        for arg in extra_args:
            if isinstance(arg, str):
                if "--width=" in arg:
                    try:
                        w = int(arg.split("=")[1])
                    except Exception:
                        pass
                elif "--height=" in arg:
                    try:
                        h = int(arg.split("=")[1])
                    except Exception:
                        pass
                elif "x" in arg:
                    try:
                        parts = arg.split("x")
                        w = int(parts[0])
                        h = int(parts[1])
                    except Exception:
                        pass
        return max(200, w), max(150, h)

    def update_config_args(self, extra_args: list):
        """Update window geometry strictly driven by config.json changes."""
        if not self.running:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        self.extra_args = extra_args
        new_w, new_h = self._parse_dimensions(extra_args)
        if new_w != self.target_w or new_h != self.target_h:
            player_logger.info(
                f"Window {self.window_id} resized via config: {self.target_w}x{self.target_h} -> {new_w}x{new_h}"
            )
            self.target_w = new_w
            self.target_h = new_h
            cur_x = self.winfo_x()
            cur_y = self.winfo_y()
            self.geometry(f"{new_w}x{new_h}+{cur_x}+{cur_y}")
            self.canvas.configure(width=new_w, height=new_h)

    def _center_window(self, w: int, h: int):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _start_drag(self, event):
        self._offset_x = event.x_root - self.winfo_x()
        self._offset_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        if not self.running:
            return
        try:
            if not self.winfo_exists():
                return
            new_x = event.x_root - self._offset_x
            new_y = event.y_root - self._offset_y
            self.geometry(f"{self.target_w}x{self.target_h}+{new_x}+{new_y}")
        except Exception:
            pass

    def _start_playback(self):
        stream_url = self.stream_info.get("stream_url")
        audio_url = self.stream_info.get("audio_url")
        if not stream_url:
            player_logger.error(f"Cannot start playback for {self.window_id}: stream_url is None")
            self.close_window()
            return

        self.buffer_thread = threading.Thread(target=self._stream_capture_loop, args=(stream_url,), daemon=True)
        self.buffer_thread.start()

        if audio_url:
            self.audio_thread = threading.Thread(target=self._audio_playback_loop, args=(audio_url,), daemon=True)
            self.audio_thread.start()
        else:
            self.audio_start_time = time.perf_counter()

        self.after(20, self._render_loop)

    def _audio_playback_loop(self, audio_url: str):
        player_logger.info(f"Opening audio buffer stream for {self.window_id}...")
        try:
            import imageio_ffmpeg
            import pyaudio

            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_bin,
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-loglevel", "quiet",
                "-i", audio_url,
                "-f", "s16le",
                "-ac", "2",
                "-ar", "44100",
                "-"
            ]
            self.audio_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=1024 * 64
            )
            self.pa = pyaudio.PyAudio()
            self.pa_stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=2,
                rate=44100,
                output=True,
                frames_per_buffer=1024
            )

            player_logger.info(f"Audio stream playing for {self.window_id}.")
            self.audio_start_time = time.perf_counter()
            self.rendered_frame_idx = 0

            while self.running and self.audio_proc:
                chunk = self.audio_proc.stdout.read(4096)
                if not chunk:
                    break
                self.pa_stream.write(chunk)
        except Exception as e:
            player_logger.error(f"Audio playback error on {self.window_id}: {e}")
        finally:
            self._cleanup_audio()

    def _cleanup_audio(self):
        if hasattr(self, 'pa_stream') and self.pa_stream:
            try:
                self.pa_stream.stop_stream()
                self.pa_stream.close()
            except Exception:
                pass
            self.pa_stream = None

        if hasattr(self, 'pa') and self.pa:
            try:
                self.pa.terminate()
            except Exception:
                pass
            self.pa = None

        if hasattr(self, 'audio_proc') and self.audio_proc:
            try:
                self.audio_proc.kill()
            except Exception:
                pass
            self.audio_proc = None

    def _stream_capture_loop(self, stream_url: str):
        player_logger.info(f"Opening video buffer stream for {self.window_id}...")
        self.cap = cv2.VideoCapture(stream_url)
        if not self.cap.isOpened():
            player_logger.error(f"Failed to open video capture stream for {self.window_id}")
            self.after(0, self.close_window)
            return

        player_logger.info(f"Stream opened successfully for {self.window_id}. Buffering frames...")
        while self.running:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                player_logger.info(f"End of stream reached for {self.window_id}.")
                break
            
            # Put into queue (blocking if full to prevent RAM runaway)
            while self.running:
                try:
                    self.frame_queue.put(frame, timeout=0.2)
                    break
                except queue.Full:
                    continue

        if self.cap:
            self.cap.release()
            self.cap = None

        if self.running:
            # Signal playback end
            self.after(50, self.close_window)

    def _render_loop(self):
        if not self.running:
            return

        if self.audio_start_time is not None:
            elapsed = time.perf_counter() - self.audio_start_time
            target_idx = int(elapsed * self.fps)

            latest_frame = None
            # Catch up video frame index to the exact audio time
            while self.rendered_frame_idx <= target_idx:
                try:
                    latest_frame = self.frame_queue.get_nowait()
                    self.rendered_frame_idx += 1
                except queue.Empty:
                    break

            if latest_frame is not None:
                try:
                    # Fast OpenCV hardware-accelerated resize (<1ms)
                    h, w = latest_frame.shape[:2]
                    if w != self.target_w or h != self.target_h:
                        latest_frame = cv2.resize(latest_frame, (self.target_w, self.target_h), interpolation=cv2.INTER_LINEAR)

                    rgb_frame = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb_frame)

                    self.photo_img = ImageTk.PhotoImage(pil_img)
                    self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_img)
                except Exception as e:
                    player_logger.error(f"Render error on {self.window_id}: {e}")

        if self.running:
            # High-precision 10ms polling to stay permanently locked to audio clock
            self.after(10, self._render_loop)

    def close_window(self):
        """Close window and trigger garbage collection."""
        if not self.running:
            return
        self.running = False
        lifecycle_logger.info(f"Closing dynamic window {self.window_id}...")

        proc = psutil.Process(os.getpid())
        ram_before = proc.memory_info().rss / (1024 * 1024)

        # Cleanup audio resources
        self._cleanup_audio()

        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        # Clear frame queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Exception:
                break

        try:
            self.destroy()
        except Exception:
            pass

        if self.on_close_cb:
            try:
                self.on_close_cb(self.window_id)
            except Exception as e:
                lifecycle_logger.error(f"Error executing on_close callback: {e}")

        # Explicit garbage collection as required
        collected = gc.collect()
        ram_after = proc.memory_info().rss / (1024 * 1024)
        lifecycle_logger.info(
            f"Garbage collector executed for {self.window_id}: "
            f"{collected} objects freed | RAM before: {ram_before:.2f} MB -> after: {ram_after:.2f} MB"
        )
