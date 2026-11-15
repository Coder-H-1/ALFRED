"""
ALFRED GUI Controller
---------------------
Coordinates the Python Tkinter IGUIRS avatar GUI and dynamic windows.
Launches the background streaming GUI and communicates state changes via IGUIRS/config.json.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
IGUIRS_DIR = ROOT_DIR / "IGUIRS"
CONFIG_PATH = IGUIRS_DIR / "config.json"
GUI_SCRIPT = IGUIRS_DIR / "renderer.py"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from FILES.logger import get_logger
    logger = get_logger("IGUIRS.Controller")
except Exception:
    import logging
    logger = logging.getLogger("IGUIRS.Controller")

_GUI_PROCESS = None

def get_current_config() -> dict:
    default_cfg = {
        "main": {
            "state": "rest",
            "fps": 30,
            "size_reduce_percentage": 0.0
        }
    }
    if not CONFIG_PATH.exists():
        return default_cfg

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Backward compatibility if root level had 'state'
        if "main" not in data:
            data = {
                "main": {
                    "state": data.get("state", "rest"),
                    "fps": data.get("fps", 30),
                    "size_reduce_percentage": data.get("size_reduce_percentage", 0.0)
                },
                **{k: v for k, v in data.items() if k not in ("state", "fps", "size_reduce_percentage")}
            }
        return data
    except Exception as e:
        logger.error(f"Error reading config from {CONFIG_PATH}: {e}")
        return default_cfg

def save_config(cfg: dict) -> bool:
    try:
        temp_path = CONFIG_PATH.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        os.replace(temp_path, CONFIG_PATH)
        return True
    except Exception as e:
        logger.error(f"Error writing config to {CONFIG_PATH}: {e}")
        return False

def set_gui_state(state: str, fps: int = None, size_reduce_pct: float = None, force: bool = False):
    """
    Update IGUIRS avatar main state via config.json.
    Guarded so state transitions do not interrupt or break active speech unless force=True.
    """
    if not force:
        try:
            from FILES.util_functions import is_speaking
            if is_speaking() and state in ("rest", "listening", "thinking"):
                logger.debug(f"Speech is actively playing; deferring state transition to '{state}'.")
                return
        except Exception:
            pass

    cfg = get_current_config()
    if "main" not in cfg:
        cfg["main"] = {}

    curr_state = cfg["main"].get("state")
    curr_fps = cfg["main"].get("fps")
    curr_reduce = cfg["main"].get("size_reduce_percentage")

    state_changed = (state is not None and curr_state != state)
    fps_changed = (fps is not None and curr_fps != int(fps))
    reduce_changed = (size_reduce_pct is not None and curr_reduce != float(size_reduce_pct))

    if not (state_changed or fps_changed or reduce_changed):
        return

    if state_changed:
        cfg["main"]["state"] = state
    if fps_changed:
        cfg["main"]["fps"] = int(fps)
    if reduce_changed:
        cfg["main"]["size_reduce_percentage"] = float(size_reduce_pct)

    logger.info(f"Updated main GUI state: state={state}, fps={fps}, size_reduce={size_reduce_pct}")
    save_config(cfg)

def add_window(win_id: str, win_type: str, data: str, extra_args: list = None):
    """
    Register a dynamic window (e.g. window_1, window_2) in config.json.
    """
    cfg = get_current_config()
    cfg[win_id] = {
        "type": win_type,
        "data": data,
        "extra-args": extra_args if extra_args is not None else []
    }
    logger.info(f"Adding dynamic window {win_id}: type={win_type}, data={data}, extra-args={extra_args}")
    save_config(cfg)

def remove_window(win_id: str):
    """
    Remove a dynamic window from config.json.
    """
    cfg = get_current_config()
    if win_id in cfg:
        del cfg[win_id]
        logger.info(f"Removed dynamic window {win_id} from config.")
        save_config(cfg)

def update_window_args(win_id: str, extra_args: list):
    """
    Update window extra arguments (e.g. size/dimensions).
    """
    cfg = get_current_config()
    if win_id in cfg and isinstance(cfg[win_id], dict):
        cfg[win_id]["extra-args"] = extra_args
        logger.info(f"Updated dynamic window {win_id} extra-args={extra_args}")
        save_config(cfg)

def get_python_executable() -> str:
    """Finds Python interpreter with required multimedia libraries without hardcoding paths."""
    try:
        import yt_dlp
        return sys.executable
    except ImportError:
        pass

    import shutil
    py_launcher = shutil.which("py")
    if py_launcher:
        for ver in ("-3.14", "-3.12", "-3"):
            try:
                res = subprocess.run(
                    [py_launcher, ver, "-c", "import yt_dlp, sys; print(sys.executable)"],
                    capture_output=True, text=True, timeout=3
                )
                cand = res.stdout.strip()
                if cand and os.path.isfile(cand):
                    return cand
            except Exception:
                pass
    return sys.executable


def launch_gui(autostart: bool = True):
    """Launch the Python Tkinter IGUIRS player if not already running."""
    global _GUI_PROCESS
    if _GUI_PROCESS is not None and _GUI_PROCESS.poll() is None:
        return _GUI_PROCESS

    # Check if renderer.py is already running as a system process
    try:
        import psutil
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd = " ".join(p.info.get('cmdline') or [])
                if "renderer.py" in cmd:
                    logger.debug(f"IGUIRS renderer already running (PID {p.pid}).")
                    return p
            except Exception:
                pass
    except Exception:
        pass

    if not GUI_SCRIPT.exists():
        logger.error(f"Renderer script not found at {GUI_SCRIPT}")
        return None

    try:
        py_exec = get_python_executable()
        logger.info(f"Launching IGUIRS renderer subprocess: {py_exec} {GUI_SCRIPT}")
        _GUI_PROCESS = subprocess.Popen(
            [py_exec, str(GUI_SCRIPT)],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return _GUI_PROCESS
    except Exception as e:
        logger.error(f"Failed to launch GUI subprocess: {e}")
        return None

def close_gui():
    """Terminate the GUI process cleanly."""
    global _GUI_PROCESS
    if _GUI_PROCESS is not None:
        try:
            if _GUI_PROCESS.poll() is None:
                logger.info("Terminating IGUIRS GUI process.")
                _GUI_PROCESS.terminate()
        except Exception as e:
            logger.error(f"Error terminating GUI process: {e}")
        _GUI_PROCESS = None


STATUS_PATH = IGUIRS_DIR / "runtime_status.json"


def get_window_status(win_id: str) -> dict:
    """
    Retrieves runtime status of a window (x, y, width, height, fps).
    Reads from runtime_status.json with fallback to config.json.
    """
    # 1. Try reading live runtime telemetry
    if STATUS_PATH.exists():
        try:
            with open(STATUS_PATH, "r", encoding="utf-8") as f:
                status_map = json.load(f)
            if win_id in status_map:
                entry = status_map[win_id]
                entry["name"] = win_id
                entry["exists"] = True
                return entry
        except Exception:
            pass

    # 2. Fallback to static config
    cfg = get_current_config()
    if win_id == "main":
        main_cfg = cfg.get("main", {})
        return {
            "name": "main",
            "exists": True,
            "status": "open",
            "state": main_cfg.get("state", "rest"),
            "x": 0,
            "y": 0,
            "width": 400,
            "height": 400,
            "fps": main_cfg.get("fps", 30)
        }

    if win_id in cfg and isinstance(cfg[win_id], dict):
        w_entry = cfg[win_id]
        extra_args = w_entry.get("extra-args", [])
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
        return {
            "name": win_id,
            "exists": True,
            "status": "open",
            "type": w_entry.get("type", "video"),
            "data": w_entry.get("data", ""),
            "x": 0,
            "y": 0,
            "width": w,
            "height": h,
            "fps": 30
        }

    return {
        "name": win_id,
        "exists": False,
        "status": "closed",
        "x": 0,
        "y": 0,
        "width": 0,
        "height": 0,
        "fps": 0
    }


def clean_all_subwindows() -> list:
    """Removes all dynamic secondary windows from config."""
    cfg = get_current_config()
    removed = []
    keys = [k for k in cfg.keys() if k != "main"]
    for k in keys:
        del cfg[k]
        removed.append(k)
    if removed:
        save_config(cfg)
        logger.info(f"Cleaned all secondary dynamic windows: {removed}")
    return removed


def show_data(items: list):
    """
    Backward compatibility wrapper for legacy show_data calls.
    Directs payloads into the dynamic window system.
    """
    if not items:
        remove_window("youtube_window")
        return

    item = str(items[0])
    if item.startswith("youtube:") or item.startswith("video:"):
        payload = item.split(":", 1)[1]
    else:
        payload = item

    launch_gui()
    add_window("youtube_window", "video", payload, ["--width=800", "--height=600"])

