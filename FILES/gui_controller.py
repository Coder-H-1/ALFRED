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
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error writing config to {CONFIG_PATH}: {e}")
        return False

def set_gui_state(state: str, fps: int = None, size_reduce_pct: float = None):
    """
    Update IGUIRS avatar main state via config.json.
    """
    cfg = get_current_config()
    if "main" not in cfg:
        cfg["main"] = {}

    cfg["main"]["state"] = state
    if fps is not None:
        cfg["main"]["fps"] = int(fps)
    if size_reduce_pct is not None:
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

def launch_gui(autostart: bool = True):
    """Launch the Python Tkinter IGUIRS player if not already running."""
    global _GUI_PROCESS
    if _GUI_PROCESS is not None and _GUI_PROCESS.poll() is None:
        return _GUI_PROCESS

    if not GUI_SCRIPT.exists():
        logger.error(f"Renderer script not found at {GUI_SCRIPT}")
        return None

    try:
        py_exec = sys.executable
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
