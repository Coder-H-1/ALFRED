import keyboard
import subprocess
import threading
import time


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


if __name__ == "__main__":    
    threading.Thread(target=wait_for_hotkey, daemon=True).start()

    # Keeps launcher running forever
    while True:
        time.sleep(0.2)