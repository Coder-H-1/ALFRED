import os
import sys
import atexit
import time
import re
import gc
import random
from collections import deque

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import version
from FILES.logger import get_logger
from FILES.log_compressor import compress_all_rotated_logs
from FILES.gui_controller import launch_gui, set_gui_state, close_gui
from FILES.LATENCY_RECORDER import LatencyRecorder
from FILES.util_functions import (
    listen_command,
    speak,
    stop_speaking,
    is_speaking,
    wait_until_done_speaking,
    get_voice_module,
)
from FILES.utils import Responder, get_greeting, MEMORY
from FILES.commands import process_command
from FILES.plugin_host import start_plugin_listener, match_dynamic_command

logger = get_logger("startup")

# Base project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_subsystems(base_dir: str = BASE_DIR):
    """Checks optional MCP and Researcher subsystems and initializes them if available."""
    mcp_dir = os.path.join(base_dir, "MCP")
    if os.path.isdir(mcp_dir):
        logger.info("MCP subsystem detected. Initializing plugin listener...")
        start_plugin_listener()
    else:
        logger.info("MCP folder not present. ALFRED operating in standalone core mode.")

    researcher_dir = os.path.join(base_dir, "Researcher")
    if os.path.isdir(researcher_dir):
        logger.info("Researcher repository detected. Deep research capabilities enabled.")
    else:
        logger.info("Researcher repository not found. Running in core mode without deep research.")


def initialize_system():
    """Performs startup initializations, environment setup, and subsystem checks."""
    logger.info(f"Starting {version.PROJECT_NAME}")
    atexit.register(compress_all_rotated_logs)
    atexit.register(close_gui)

    # Launch GUI avatar in background
    launch_gui()
    set_gui_state("work")

    # Initialize latency recorder and log startup
    latency = LatencyRecorder()
    latency.startup_record()

    speak("System is now fully operational.")
    os.system(f"title {version.PROJECT_NAME}")
    os.system("cls")

    speak(get_greeting())

    # Run subsystem presence checks & listeners
    check_subsystems(BASE_DIR)

    wait_until_done_speaking()
    set_gui_state("rest")

    # When background voice synthesis finishes, automatically return GUI avatar to rest
    try:
        get_voice_module().on_speech_finished = lambda: set_gui_state("rest", force=True)
    except Exception as e:
        logger.warning(f"Could not bind on_speech_finished: {e}")

    return {
        "latency": latency,
        "logger": logger,
    }


__all__ = [
    # Built-in / third-party re-exports
    "os",
    "sys",
    "time",
    "re",
    "gc",
    "random",
    "deque",
    "version",
    # Core services & utilities
    "logger",
    "get_logger",
    "LatencyRecorder",
    "launch_gui",
    "set_gui_state",
    "close_gui",
    "listen_command",
    "speak",
    "stop_speaking",
    "is_speaking",
    "wait_until_done_speaking",
    "get_voice_module",
    "Responder",
    "get_greeting",
    "MEMORY",
    "process_command",
    "start_plugin_listener",
    "match_dynamic_command",
    # Startup routines
    "check_subsystems",
    "initialize_system",
    "BASE_DIR",
]

