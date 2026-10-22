"""
IGUIRS Window Process Runner
----------------------------
Independent process runner for dynamic secondary windows.
Runs each dynamic window (video player, selection modal, etc.) in its own OS process
with an isolated Tkinter event loop.

If this process crashes or closes, the main IGUIRS HUD process remains completely unaffected.
"""

import os
import sys
import json
import time
import threading
from pathlib import Path
import tkinter as tk

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
CONFIG_PATH = BASE_DIR / "config.json"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from FILES.logger import get_logger
    logger = get_logger("IGUIRS.WindowProcess")
except Exception:
    import logging
    logger = logging.getLogger("IGUIRS.WindowProcess")

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


class IsolatedWindowRunner:
    def __init__(self, window_id: str):
        self.window_id = window_id
        self.running = True
        self.player_window = None
        self.current_extra_args = []

        # Create isolated Tkinter root
        self.root = tk.Tk()
        self.root.withdraw()  # Root stays hidden; child windows (Toplevel) are shown

        # Read initial window info from config.json
        win_data = self._read_window_data()
        if not win_data:
            logger.error(f"Window ID '{window_id}' not found in {CONFIG_PATH}. Exiting process.")
            sys.exit(1)

        self.win_type = win_data.get("type", "video")
        self.raw_data = win_data.get("data", "")
        self.current_extra_args = win_data.get("extra-args", [])

        # Start background config watcher for this specific window
        self.watcher_thread = threading.Thread(target=self._watch_config_loop, daemon=True)
        self.watcher_thread.start()

        # Start setup workflow
        self.root.after(0, self._start_window_pipeline)

    def _read_config(self) -> dict:
        if not CONFIG_PATH.exists():
            return {}
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _read_window_data(self) -> dict:
        cfg = self._read_config()
        return cfg.get(self.window_id)

    def _cleanup_config(self):
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if self.window_id in cfg:
                    del cfg[self.window_id]
                    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=4)
                    logger.info(f"Cleaned up '{self.window_id}' from config.")
        except Exception as e:
            logger.error(f"Error cleaning {self.window_id} from config: {e}")

    def _watch_config_loop(self):
        last_mtime = None
        while self.running:
            try:
                if CONFIG_PATH.exists():
                    mtime = os.path.getmtime(CONFIG_PATH)
                    if mtime != last_mtime:
                        last_mtime = mtime
                        cfg = self._read_config()
                        if self.window_id not in cfg:
                            logger.info(f"Window '{self.window_id}' removed from config. Closing process.")
                            self.root.after(0, self._shutdown)
                            break

                        # Check for dimension or argument changes
                        new_extra_args = cfg[self.window_id].get("extra-args", [])
                        if new_extra_args != self.current_extra_args:
                            self.current_extra_args = new_extra_args
                            if self.player_window:
                                self.root.after(0, self.player_window.update_config_args, new_extra_args)
            except Exception:
                pass
            time.sleep(0.2)

    def _start_window_pipeline(self):
        if self.win_type in ("video", "yt_video", "stream"):
            threading.Thread(target=self._resolve_video_options, daemon=True).start()
        else:
            logger.warning(f"Unsupported window type '{self.win_type}' for {self.window_id}")
            self._shutdown()

    def _resolve_video_options(self):
        try:
            options = search_video_options(self.raw_data)
            if not options:
                logger.warning(f"No video options found for '{self.raw_data}'. Exiting.")
                self.root.after(0, self._shutdown)
                return

            is_direct_url = any(domain in self.raw_data for domain in ("youtube.com/watch", "youtu.be/", "vimeo.com"))
            if len(options) == 1 and is_direct_url:
                self._on_video_selected(options[0])
            else:
                def show_modal():
                    VideoSelectorModal(
                        self.root,
                        self.raw_data,
                        options,
                        self._on_video_selected
                    )
                self.root.after(0, show_modal)
        except Exception as e:
            logger.error(f"Error in video options search: {e}")
            self.root.after(0, self._shutdown)

    def _on_video_selected(self, chosen: dict):
        if not chosen:
            logger.info(f"Option selection cancelled for {self.window_id}.")
            self.root.after(0, self._shutdown)
            return

        def fetch_stream():
            try:
                logger.info(f"Resolving stream source for {chosen.get('title')}...")
                stream_info = resolve_stream_source(chosen["url"])

                def launch_player():
                    self.player_window = DynamicVideoWindow(
                        self.root,
                        window_id=self.window_id,
                        stream_info=stream_info,
                        extra_args=self.current_extra_args,
                        on_close=lambda wid: self._shutdown()
                    )
                    logger.info(f"Dynamic video player started in isolated process (PID: {os.getpid()})")

                self.root.after(0, launch_player)
            except Exception as e:
                logger.error(f"Error fetching stream for {self.window_id}: {e}")
                self.root.after(0, self._shutdown)

        threading.Thread(target=fetch_stream, daemon=True).start()

    def _shutdown(self):
        if not self.running:
            return
        self.running = False
        logger.info(f"Terminating isolated window process for '{self.window_id}' (PID: {os.getpid()})")
        self._cleanup_config()

        if self.player_window:
            try:
                self.player_window.close_window()
            except Exception:
                pass
            self.player_window = None

        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m IGUIRS.window_process <window_id>")
        sys.exit(1)

    win_id_arg = sys.argv[1]
    runner = IsolatedWindowRunner(win_id_arg)
    runner.run()
