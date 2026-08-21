"""
`plugin_host.py` — Octopus Framework Bridge for ALFRED

This module connects the Octopus Framework's compiled plugins to ALFRED's main command loop.
"""

import os
import socket
import threading
import traceback
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

# Import port configuration from version control file
try:
    from version import PLUGIN_SOCKET_HOST as HOST, PLUGIN_SOCKET_PORT as PORT
except ImportError:
    HOST = "127.0.0.1"
    PORT = 65432

logger = get_logger(__name__)

# ─── Plugin Registry ──────────────────────────────────────────────────────────
DYNAMIC_COMMANDS: dict = {}

# ─── Paths ────────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Project root (AI/)
_COMPILED_DIR = os.path.join(_BASE_DIR, "FmWk", "compiled_plugins")


@track_latency("plugin_host.load_compiled_plugins")
def load_compiled_plugins() -> int:
    """
    Scans FmWk/compiled_plugins/ and exec()s every .py file into DYNAMIC_COMMANDS.
    Called once at ALFRED startup.
    Returns the number of plugins loaded.
    """
    if not os.path.isdir(_COMPILED_DIR):
        logger.warning(f"Plugin directory not found: {_COMPILED_DIR}")
        return 0

    loaded = 0
    for filename in os.listdir(_COMPILED_DIR):
        if not filename.endswith(".py"):
            continue

        filepath = os.path.join(_COMPILED_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
            inject_payload(code, source=filename)
            loaded += 1
        except Exception as e:
            logger.error(f"Failed to load plugin {filename}: {e}", exc_info=True)

    logger.info(f"Loaded {loaded} compiled plugin(s) from disk.")
    return loaded


@track_latency("plugin_host.inject_payload")
def inject_payload(payload: str, source: str = "socket") -> None:
    """
    Executes a compiled Python payload string inside a namespace
    that includes the shared DYNAMIC_COMMANDS dictionary.
    """
    namespace = {"DYNAMIC_COMMANDS": DYNAMIC_COMMANDS}

    try:
        from FILES.utils import Responder
        namespace["Responder"] = Responder
    except Exception as e:
        logger.debug(f"Responder not available for plugin namespace: {e}")

    try:
        exec(payload, namespace)
        logger.info(f"Injected payload from source: {source}")
    except Exception as e:
        logger.error(f"Payload injection error ({source}): {e}")
        logger.error(traceback.format_exc())


@track_latency("plugin_host.match_dynamic_command")
def match_dynamic_command(command: str):
    """
    Iterates over all registered DYNAMIC_COMMANDS and calls each handler.
    Returns the first non-None response, or None if no plugin matched.
    """
    for trigger, handler in DYNAMIC_COMMANDS.items():
        try:
            result = handler(command)
            if result is not None:
                logger.info(f"Dynamic command matched by plugin trigger '{trigger}'")
                return result
        except Exception as e:
            logger.error(f"Error in dynamic command plugin trigger '{trigger}': {e}", exc_info=True)
    return None


def _socket_listener():
    """
    Background TCP server that receives payloads from the Octopus Framework CLI/IDE.
    Runs in a daemon thread — dies when ALFRED exits.
    """
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        logger.info(f"Octopus socket listener active on {HOST}:{PORT}")

        while True:
            conn, addr = server.accept()
            try:
                data = conn.recv(65536).decode("utf-8")

                if data.strip() == "STATUS_CHECK":
                    count = len(DYNAMIC_COMMANDS)
                    response = f"ALFRED Online | {count} plugin command(s) loaded."
                    conn.sendall(response.encode("utf-8"))
                else:
                    logger.info(f"Received payload socket connection from {addr}")
                    inject_payload(data, source=f"socket@{addr[0]}")
                    conn.sendall("OK: Plugin injected successfully.".encode("utf-8"))

            except Exception as e:
                logger.error(f"Connection/socket error: {e}", exc_info=True)
                try:
                    conn.sendall(f"ERROR: {e}".encode("utf-8"))
                except Exception:
                    pass
            finally:
                conn.close()

    except OSError as e:
        logger.error(f"Could not start listener on port {PORT}: {e}")
        logger.error("Is another instance of ALFRED or Octopus already running?")


@track_latency("plugin_host.start_plugin_listener")
def start_plugin_listener():
    """
    Loads all existing compiled plugins, then starts the background socket listener.
    Call this once during ALFRED's initialization.
    """
    logger.info("Initializing plugin listener...")
    load_compiled_plugins()

    listener_thread = threading.Thread(target=_socket_listener, daemon=True)
    listener_thread.start()
    logger.info("Plugin listener thread started.")
