import subprocess
import threading
import time
import os
import sys
import keyboard
import plyer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import default backend URL fallback
try:
    from version import PROJECT_NAME
except ImportError:
    PROJECT_NAME = "ALFRED"

alfred_process = None


def notify_startup():
    try:
        plyer.notification.notify(
            title=f"{PROJECT_NAME} Activated",
            message="Launcher running in background.",
            app_name=PROJECT_NAME,
            timeout=5
        )
    except Exception:
        pass


def launch_alfred():
    global alfred_process
    if alfred_process is not None and alfred_process.poll() is None:
        try:
            plyer.notification.notify(
                title=PROJECT_NAME,
                message="ALFRED is already running.",
                app_name=PROJECT_NAME,
                timeout=3
            )
        except Exception:
            pass
        return

    try:
        creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
        alfred_process = subprocess.Popen(
            ["py", "-3.14", MAIN_SCRIPT],
            cwd=BASE_DIR,
            creationflags=creationflags
        )
    except Exception as e:
        try:
            plyer.notification.notify(
                title=f"{PROJECT_NAME} Error",
                message=f"Failed to start: {e}",
                app_name=PROJECT_NAME,
                timeout=5
            )
        except Exception:
            pass


def wait_for_hotkey():
    while True:
        try:
            # Wait for activation combination
            keyboard.wait("alt+shift+a+s")
            # Wait for sequential press of 'd' or chord hold
            t0 = time.time()
            triggered = False
            while time.time() - t0 < 1.0:
                if keyboard.is_pressed("d"):
                    triggered = True
                    break
                time.sleep(0.05)

            if triggered:
                launch_alfred()
                time.sleep(1.0)
        except Exception:
            time.sleep(0.5)


if __name__ == "__main__":    
    notify_startup()

    if "--profile" in os.sys.argv:
        try:
            import profiling.tracing as tracing
            profiler = tracing.Profile()
            profiler.enable()
        except Exception:
            profiler = None
    else:
        profiler = None

    threading.Thread(target=wait_for_hotkey, daemon=True).start()

    # Keeps launcher running forever
    try:
        while True:
            time.sleep(0.2)
    finally:
        if profiler:
            profiler.disable()
            profiler.print_stats()