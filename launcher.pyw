"""

## PLACE A SHORTCUT OF THIS FILE IN "STARTUP MENU" FOLDER 

Basically a hotkey detector that works in background (without a window)
On start of launcher.pyw, a windows notification is sent.

HOTKEY -> alt + shift + a + s (and while HOLDING then after 0.1 second press) + d

"""

import keyboard
import subprocess
import threading
import time

from plyer import notification


notification.notify(
    title="ALFRED Activated",
    message="Working now.",
    app_name="Alfred.",
    timeout=5
    )




def wait_for_hotkey():
    while True:
        keyboard.wait("alt+shift+a+s")  
        time.sleep(0.05)  # Wait for sequential press
        if keyboard.is_pressed("d"):
            subprocess.Popen(['python', "main.py"])



if __name__ == "__main__":    
    threading.Thread(target=wait_for_hotkey, daemon=True).start()

    # Keeps launcher running forever
    while True:
        time.sleep(0.3)