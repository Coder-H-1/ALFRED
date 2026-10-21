import subprocess
import threading
import time
import os
lazy import keyboard
lazy import plyer

# Import default backend URL fallback
try:
    from version import PROJECT_NAME
except ImportError:
    PROJECT_NAME = "ALFRED"

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


def wait_for_hotkey():
    while True:
        # Wait for activation combination
        keyboard.wait("alt+shift+a+s")  
        time.sleep(0.1)  # Wait for sequential press
        if keyboard.is_pressed("d"):
            # Launch main.pyw or main.py depending on environment
            subprocess.Popen(['python', "main.py"])


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