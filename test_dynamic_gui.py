"""
Interactive Test for IGUIRS Dynamic Window System
-------------------------------------------------
Launches the IGUIRS renderer GUI, prompts user in terminal for video
queries or URLs, updates config.json, and tests multi-window rendering.
"""

import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from FILES.gui_controller import (
    launch_gui,
    close_gui,
    get_current_config,
    set_gui_state,
    add_window,
    remove_window,
    update_window_args
)
from FILES.logger import get_logger

logger = get_logger("IGUIRS.TestRunner")


def test_interactive_gui():
    print("=" * 60)
    print("      IGUIRS DYNAMIC WINDOW INTERACTIVE TEST RUNNER")
    print("=" * 60)

    # 1. Start GUI Renderer Subprocess
    print("\n[1/2] Launching IGUIRS renderer...")
    proc = launch_gui()
    if not proc:
        print("ERROR: Failed to launch IGUIRS renderer.")
        return

    time.sleep(1.0)
    print("IGUIRS renderer running! (PID: {})\n".format(proc.pid))

    print("COMMANDS:")
    print("  - Enter search query or URL to spawn a dynamic video window (default: 800x600)")
    print("  - 'state <name>' (e.g. 'state thinking', 'state work', 'state rest')")
    print("  - 'resize <win_id> <w> <h>' (e.g. 'resize window_1 1024 768')")
    print("  - 'close <win_id>' (e.g. 'close window_1')")
    print("  - 'q' or 'quit' to close GUI and exit\n")

    win_counter = 1

    try:
        while True:
            if proc.poll() is not None:
                print("\n[!] Notice: Renderer process stopped.")
                break

            try:
                cmd = input("IGUIRS-Test > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not cmd:
                continue

            if cmd.lower() in ("q", "quit", "exit"):
                break

            if cmd.startswith("state "):
                new_state = cmd.split(maxsplit=1)[1].strip()
                set_gui_state(new_state)
                print(f"[OK] Main state updated to: '{new_state}'")
                continue

            if cmd.startswith("resize "):
                parts = cmd.split()
                if len(parts) >= 4:
                    w_id, w_w, w_h = parts[1], parts[2], parts[3]
                    update_window_args(w_id, [f"--width={w_w}", f"--height={w_h}"])
                    print(f"[OK] Config resize triggered for {w_id} -> {w_w}x{w_h}")
                else:
                    print("Usage: resize <window_id> <width> <height>")
                continue

            if cmd.startswith("close "):
                w_id = cmd.split(maxsplit=1)[1].strip()
                remove_window(w_id)
                print(f"[OK] Removed {w_id} from config.json")
                continue

            # Otherwise, interpret as video search query or URL
            win_id = f"window_{win_counter}"
            win_counter += 1

            print(f"[+] Registering {win_id} with query/url: '{cmd}' (800x600)")
            add_window(win_id, "video", cmd, ["--width=800", "--height=600"])
            print(f"[OK] Updated config.json. Watch for option selector dialog or video window!\n")

    finally:
        print("\nCleaning up and closing IGUIRS...")
        close_gui()
        print("[OK] Test complete.")


if __name__ == "__main__":
    test_interactive_gui()
