"""
IGUIRS - Independent GUI Rendering System (Direct Frame Renderer & Multi-Window Manager)
-----------------------------------------------------------------------------------------
Streams animation frames directly from compressed GIF containers to main frame window.
Parallelly manages dynamic secondary windows (video streaming buffers, yt-dlp option selection,
frameless 800x600 windows, config-only resizing, and automatic garbage collection).
"""

import os
import sys
import json
import time
import random
import psutil
import threading
import subprocess
from pathlib import Path
from PIL import Image, ImageTk
import tkinter as tk

# Paths
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
CONFIG_PATH = BASE_DIR / "config.json"
GRAPHICS_DIR = BASE_DIR / "Graphics"
GIFS_DIR = GRAPHICS_DIR / "gifs"
WINDOW_PROCESS_SCRIPT = BASE_DIR / "window_process.py"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from FILES.logger import get_logger
    logger = get_logger("IGUIRS.Renderer")
    dyn_logger = get_logger("IGUIRS.DynamicWindow")
except Exception:
    import logging
    logger = logging.getLogger("IGUIRS.Renderer")
    dyn_logger = logging.getLogger("IGUIRS.DynamicWindow")

# Import video engine
try:
    from IGUIRS.video_engine import (
        search_video_options,
        resolve_stream_source,
        VideoSelectorModal,
        DynamicVideoWindow
    )
except ImportError:
    from video_engine import (
        search_video_options,
        resolve_stream_source,
        VideoSelectorModal,
        DynamicVideoWindow
    )


class IguirsRenderer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("IGUIRS - Direct Stream Renderer")
        self.root.configure(bg="#000000")
        
        # Make main window sleek, frameless or modern
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)  # Frameless for clean HUD avatar display

        # Main window dragging state
        self._offset_x = 0
        self._offset_y = 0
        self.root.bind("<Button-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._do_drag)

        # Hotkeys
        self.root.bind("<Escape>", lambda e: self.quit())
        self.root.bind("q", lambda e: self.quit())
        self.root.bind("1", lambda e: self.set_state("rest"))
        self.root.bind("2", lambda e: self.set_state("listening"))
        self.root.bind("3", lambda e: self.set_state("thinking"))
        self.root.bind("4", lambda e: self.set_state("work"))

        # Display Label for Main HUD
        self.display_label = tk.Label(self.root, bg="#000000", bd=0, highlightthickness=0)
        self.display_label.pack(fill=tk.BOTH, expand=True)
        self.display_label.bind("<Button-1>", self._start_drag)
        self.display_label.bind("<B1-Motion>", self._do_drag)

        # Config state
        self.current_state = "rest"
        self.target_fps = 30
        self.size_reduce_percentage = 0.0
        self.current_scale = 1.0

        # Animation state
        self.current_gif_path = None
        self.gif_frames = []
        self.frame_index = 0
        self.last_frame_time = time.time()
        self.running = True

        # Dynamic windows registry
        self.dynamic_windows = {}  # {window_id: DynamicVideoWindow instance}
        self.pending_windows = set()

        # Process monitor
        self.process = psutil.Process(os.getpid())

        # Ensure gifs exist
        self._ensure_gifs()

        # Load initial state
        self._load_config()
        self._load_state_media(self.current_state)

        # Start background config watcher
        self.watcher_thread = threading.Thread(target=self._watch_config_loop, daemon=True)
        self.watcher_thread.start()

        # Center initial window
        self._center_window()

        # Start playback loop
        self.root.after(10, self._render_next_frame)

    def _start_drag(self, event):
        self._offset_x = event.x_root - self.root.winfo_x()
        self._offset_y = event.y_root - self.root.winfo_y()

    def _do_drag(self, event):
        if not self.running:
            return
        try:
            new_x = event.x_root - self._offset_x
            new_y = event.y_root - self._offset_y
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            self.root.geometry(f"{w}x{h}+{new_x}+{new_y}")
        except Exception:
            pass

    def _center_window(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = int(400 * self.current_scale)
        h = int(400 * self.current_scale)
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _ensure_gifs(self):
        """Ensure state folders and default containers exist."""
        GIFS_DIR.mkdir(parents=True, exist_ok=True)
        for state_dir_name in ("listening", "rest", "thinking", "work"):
            (GIFS_DIR / state_dir_name).mkdir(parents=True, exist_ok=True)

        mappings = {
            "rest": GRAPHICS_DIR / "rest",
            "work": GRAPHICS_DIR / "work",
            "thinking": GRAPHICS_DIR / "thinking",
        }
        for state_name, folder in mappings.items():
            gif_file = GIFS_DIR / f"{state_name}.gif"
            if not gif_file.exists() and folder.exists():
                logger.info(f"Assembling {gif_file.name} from {folder}...")
                png_files = sorted([folder / f for f in os.listdir(folder) if f.endswith(".png")])
                if png_files:
                    imgs = [Image.open(p).convert("RGBA") for p in png_files]
                    imgs[0].save(
                        gif_file,
                        save_all=True,
                        append_images=imgs[1:],
                        duration=int(1000 / 30),
                        loop=0,
                        optimize=True,
                    )
                    logger.info(f"Created {gif_file} ({gif_file.stat().st_size} bytes)")

    def _get_state_gifs(self, state_name: str):
        """Find all GIF files for a state from dedicated folders or fallback files."""
        candidates = []
        for base in (GIFS_DIR, GRAPHICS_DIR):
            folder = base / state_name
            if folder.is_dir():
                for p in folder.iterdir():
                    if p.is_file() and p.suffix.lower() == ".gif":
                        candidates.append(p)

        if candidates:
            return sorted(list(set(candidates)))

        for base in (GIFS_DIR, GRAPHICS_DIR):
            for pattern in (f"{state_name}.gif", f"{state_name}*.gif"):
                for p in base.glob(pattern):
                    if p.is_file() and p.suffix.lower() == ".gif":
                        candidates.append(p)
            if candidates:
                return sorted(list(set(candidates)))

        aliases = {"rest2": "rest"}
        if state_name in aliases:
            return self._get_state_gifs(aliases[state_name])

        return []

    def _load_config(self):
        if not CONFIG_PATH.exists():
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Separate main window configuration
            main_cfg = data.get("main", {})
            if not main_cfg and "state" in data:
                main_cfg = data

            self.current_state = main_cfg.get("state", "rest")
            self.target_fps = max(1, main_cfg.get("fps", 30))
            self.size_reduce_percentage = main_cfg.get("size_reduce_percentage", 0.0)
            self.current_scale = max(0.05, min(5.0, (100.0 - self.size_reduce_percentage) / 100.0))

            # Synchronize dynamic windows
            self._sync_dynamic_windows(data)
        except Exception as e:
            logger.error(f"Error reading config: {e}")

    def _sync_dynamic_windows(self, full_config: dict):
        """
        Manage dynamic secondary windows as isolated OS processes.
        """
        active_window_keys = {
            k: v for k, v in full_config.items()
            if (k.startswith("window_") or (k != "main" and isinstance(v, dict) and "type" in v))
        }

        # 1. Spawn new dynamic window processes
        for win_id, win_data in active_window_keys.items():
            if win_id not in self.dynamic_windows and win_id not in self.pending_windows:
                self.pending_windows.add(win_id)
                dyn_logger.info(f"Discovered new dynamic window '{win_id}': {win_data}")
                self._spawn_dynamic_window(win_id, win_data)
            elif win_id in self.dynamic_windows:
                proc = self.dynamic_windows[win_id]
                if proc.poll() is not None:
                    dyn_logger.info(f"Dynamic window '{win_id}' process exited (code {proc.returncode}).")
                    self.dynamic_windows.pop(win_id, None)
                    self._cleanup_config_entry(win_id)

        # 2. Terminate removed window processes
        current_tracked = list(self.dynamic_windows.keys())
        for win_id in current_tracked:
            if win_id not in active_window_keys:
                dyn_logger.info(f"Window '{win_id}' removed from config. Terminating child process.")
                proc = self.dynamic_windows.pop(win_id, None)
                if proc and proc.poll() is None:
                    try:
                        proc.terminate()
                    except Exception:
                        pass

    def _spawn_dynamic_window(self, win_id: str, win_data: dict):
        win_type = win_data.get("type", "video")
        dyn_logger.info(f"Spawning isolated window process for '{win_id}' (type '{win_type}')...")
        try:
            proc = subprocess.Popen([sys.executable, str(WINDOW_PROCESS_SCRIPT), win_id])
            self.dynamic_windows[win_id] = proc
            self.pending_windows.discard(win_id)
            dyn_logger.info(f"Dynamic window '{win_id}' running in isolated process (PID: {proc.pid})")
        except Exception as e:
            dyn_logger.error(f"Failed to spawn window process for {win_id}: {e}")
            self.pending_windows.discard(win_id)
            self._cleanup_config_entry(win_id)

    def _cleanup_config_entry(self, win_id: str):
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if win_id in cfg:
                    del cfg[win_id]
                    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=4)
                    dyn_logger.info(f"Cleaned up {win_id} from {CONFIG_PATH}")
        except Exception as e:
            dyn_logger.error(f"Error cleaning {win_id} from config: {e}")

    def _watch_config_loop(self):
        last_mtime = None
        while self.running:
            try:
                if CONFIG_PATH.exists():
                    mtime = os.path.getmtime(CONFIG_PATH)
                    if mtime != last_mtime:
                        last_mtime = mtime
                        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                            cfg = json.load(f)

                        # 1. Main window changes
                        main_cfg = cfg.get("main", {})
                        if not main_cfg and "state" in cfg:
                            main_cfg = cfg

                        new_state = main_cfg.get("state", self.current_state)
                        new_fps = max(1, main_cfg.get("fps", self.target_fps))
                        new_reduce = main_cfg.get("size_reduce_percentage", self.size_reduce_percentage)

                        if new_state != self.current_state:
                            logger.info(f"Main state change: {self.current_state} -> {new_state}")
                            self.root.after(0, self.set_state, new_state)

                        if new_fps != self.target_fps:
                            logger.info(f"Main FPS change: {self.target_fps} -> {new_fps}")
                            self.target_fps = new_fps

                        if abs(new_reduce - self.size_reduce_percentage) > 0.01:
                            self.size_reduce_percentage = new_reduce
                            self.current_scale = max(0.05, min(5.0, (100.0 - self.size_reduce_percentage) / 100.0))
                            logger.info(f"Main scale change: reduce={new_reduce}% scale={self.current_scale:.2f}")

                        # 2. Dynamic windows changes
                        self._sync_dynamic_windows(cfg)
            except Exception as e:
                pass
            time.sleep(0.2)

    def set_state(self, new_state):
        state_changed = (new_state != self.current_state)
        self.current_state = new_state
        if state_changed or not hasattr(self, 'current_im') or not self.current_im:
            self._load_state_media(new_state)

    def _load_state_media(self, state_name):
        gif_candidates = self._get_state_gifs(state_name)
        if not gif_candidates:
            logger.warning(f"No GIF found for state '{state_name}'")
            return

        if len(gif_candidates) > 1 and hasattr(self, 'current_gif_path') and self.current_gif_path:
            choices = [g for g in gif_candidates if g != self.current_gif_path]
            gif_file = random.choice(choices) if choices else random.choice(gif_candidates)
        else:
            gif_file = random.choice(gif_candidates)

        self.current_gif_path = gif_file

        start_t = time.perf_counter()
        logger.info(f"Opening container: {gif_file.name} (streaming mode, state '{state_name}')...")

        if hasattr(self, 'current_im') and self.current_im:
            try:
                self.current_im.close()
            except Exception:
                pass

        self.current_im = Image.open(gif_file)
        self.total_frames = getattr(self.current_im, 'n_frames', 1)
        self.frame_index = 0
        dur_ms = (time.perf_counter() - start_t) * 1000

        ram_mb = self.process.memory_info().rss / (1024 * 1024)
        logger.info(
            f"Ready '{state_name}' ({gif_file.name}): {self.total_frames} frames streamable in {dur_ms:.1f}ms | Process RAM: {ram_mb:.1f} MB"
        )

    def _render_next_frame(self):
        if not self.running:
            return

        if hasattr(self, 'current_im') and self.current_im and self.total_frames > 0:
            try:
                self.current_im.seek(self.frame_index)
                raw_frame = self.current_im.convert("RGBA")

                orig_w, orig_h = raw_frame.size
                target_w = max(10, int(orig_w * self.current_scale))
                target_h = max(10, int(orig_h * self.current_scale))

                if target_w != orig_w or target_h != orig_h:
                    render_img = raw_frame.resize((target_w, target_h), Image.Resampling.BILINEAR)
                else:
                    render_img = raw_frame

                tk_img = ImageTk.PhotoImage(render_img)
                self.display_label.configure(image=tk_img)
                self.display_label.image = tk_img

                cur_w = self.root.winfo_width()
                cur_h = self.root.winfo_height()
                if abs(cur_w - target_w) > 2 or abs(cur_h - target_h) > 2:
                    self.root.geometry(f"{target_w}x{target_h}")

                next_index = self.frame_index + 1
                if next_index >= self.total_frames:
                    self.frame_index = 0
                    gif_candidates = self._get_state_gifs(self.current_state)
                    if len(gif_candidates) > 1:
                        self._load_state_media(self.current_state)
                else:
                    self.frame_index = next_index
            except Exception:
                pass

        delay_ms = max(5, int(1000 / self.target_fps))
        self.root.after(delay_ms, self._render_next_frame)

    def quit(self):
        self.running = False
        # Terminate all active isolated window processes
        for win_id, proc in list(self.dynamic_windows.items()):
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        self.root.destroy()
        sys.exit(0)

    def run(self):
        logger.info("Starting Tkinter event loop for main HUD and dynamic windows.")
        self.root.mainloop()


# Backward compatibility alias
GifVideoPlayer = IguirsRenderer

if __name__ == "__main__":
    renderer = IguirsRenderer()
    renderer.run()
