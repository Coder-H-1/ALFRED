import keyboard
import subprocess
import threading
import time
import os
import requests
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

from plyer import notification

# Import default backend URL fallback
try:
    from version import PROJECT_NAME
except ImportError:
    PROJECT_NAME = "ALFRED"

notification.notify(
    title=f"{PROJECT_NAME} Activated",
    message="Launcher running in background.",
    app_name=PROJECT_NAME,
    timeout=5
)


def wait_for_hotkey():
    while True:
        # Wait for activation combination
        keyboard.wait("alt+shift+a+s")  
        time.sleep(0.1)  # Wait for sequential press
        if keyboard.is_pressed("d"):
            # Launch main.pyw or main.py depending on environment
            subprocess.Popen(['python', "main.py"])


def poll_health():
    backend_url = os.getenv("RENDER_BACKEND_URL")
    while True:
        try:
            # Strip trailing slash and hit backend health endpoint
            requests.get(f"{backend_url.rstrip('/')}/health", timeout=10)
        except Exception:
            pass
        # Poll every 4 minutes (240s)
        time.sleep(240)


if __name__ == "__main__":    
    threading.Thread(target=wait_for_hotkey, daemon=True).start()
    threading.Thread(target=poll_health, daemon=True).start()

    # Keeps launcher running forever
    while True:
        time.sleep(0.2)