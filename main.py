from FILES.utils import Responder, get_greeting, MEMORY
from FILES.commands import process_command
from FILES.util_functions import listen_command, speak, stop_speaking, is_speaking
from FILES.plugin_host import start_plugin_listener, match_dynamic_command
from FILES.log_compressor import compress_all_rotated_logs
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import LatencyRecorder
from FILES.gui_controller import launch_gui, set_gui_state, close_gui
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

logger = get_logger(__name__)

def filter_speech(text):
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    return text.strip()

COMMAND_INPUT = False  # False: listen audio command, True: console text input


def Command() -> str:
    if COMMAND_INPUT:
        try:
            cmd = input(f"[{version.PROJECT_NAME}] Enter command: ").strip()
            return cmd.lower() if cmd else None
        except (KeyboardInterrupt, EOFError):
            return "exit"
    else: 
        command = listen_command()
        return command


def main():
    global COMMAND_INPUT
    
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
    set_gui_state("rest")
    start_plugin_listener()
    interrupted_speech = False
    message_queue = deque()

    def handle_query_execution(command_text: str, q_start: float = None):
        nonlocal interrupted_speech
        if q_start is None:
            q_start = time.time()

        # Check if user says continue previous command or interrupted speech
        continue_keywords = (
            "continue the previous command",
            "continue the speech for previous command interrupted",
            "continue the speech for the previous command interrupted",
            "continue the previous speech",
            "continue previous command",
            "continue the speech",
            "continue speech",
            "continue interrupted command",
            "continue interrupted speech",
            "continue",
        )
        if any(command_text == kw or command_text.startswith(kw) for kw in continue_keywords):
            logger.info("Continue command received. Recalling previous speech from Long Term Memory...")
            prev_speech = MEMORY.get_last_assistant_response()
            if prev_speech:
                clean_prev_speech = filter_speech(prev_speech)
                speak(clean_prev_speech)
                logger.info("Resynthesised and speaking previous speech from LTM.")
            else:
                speak("I have no previous speech in memory to continue, sir.")
            interrupted_speech = False
            return

        # If user does not say continue:
        # Stop synthesizing previous text and clean memory using garbage collector
        if interrupted_speech:
            stop_speaking()
            gc.collect()
            interrupted_speech = False

        global COMMAND_INPUT
        if "switch command" in command_text:
            COMMAND_INPUT = not COMMAND_INPUT
            logger.info(f"Switched COMMAND_INPUT mode to: {COMMAND_INPUT}")
            return
        
        if any(kw in command_text for kw in ("restart yourself", "restart yourselves", "restart your self", "restart your")):
            logger.info("Restart command received. Restarting main.py process...")
            os.system("py -3.14 .\\main.py")
            close_gui()
            sys.exit()

        if any(kw in command_text for kw in ("exit", "goodbye", "bye alfred", "shutdown yourself", "you may sleep now")):
            logger.info("Exit command received. Ending memory session and exiting.")
            set_gui_state("rest")
            MEMORY.session_end()
            speak(Responder("good day alfred. Now you may close yourself."))
            close_gui()
            sys.exit()
            
        set_gui_state("thinking")
        plugin_result = match_dynamic_command(command_text)
        if plugin_result:
            logger.info("Dynamic plugin matched successfully.")
            plugin_result_clean = str(plugin_result).replace("[KEEP_UI]", "").strip()
            clean_plugin_result = filter_speech(plugin_result_clean)
            set_gui_state("work")
            speak(clean_plugin_result)
            MEMORY.add_to_history(command_text, plugin_result)
        else:
            system_action = process_command(command_text)
            if system_action:
                logger.info("System action matched successfully.")
                system_action_clean = str(system_action).replace("[KEEP_UI]", "").strip()
                clean_system_action = filter_speech(system_action_clean)
                set_gui_state("work")
                speak(clean_system_action)
                MEMORY.add_to_history(command_text, system_action)
            else:
                logger.info("No system action matched. Falling back to default Responder...")
                response = Responder(command_text)
                clean_response = filter_speech(response)
                set_gui_state("work")
                speak(clean_response) 
        
        # Record latency for this command cycle
        q_end = time.time()
        latency.record(
            source="main.command_loop",
            query_length=len(command_text) if command_text else 0,
            query_received_at=q_start,
            output_at=q_end
        )
        set_gui_state("rest")

    while True:
        try:
            # If items in queue and not currently processing/speaking, process next queued item
            if message_queue and not is_speaking():
                set_gui_state("rest")
                next_cmd = message_queue.popleft()
                logger.info(f"Processing next query from queue ({len(message_queue)} remaining): '{next_cmd}'")
                handle_query_execution(next_cmd)
                set_gui_state("rest")
                continue

            q_start = time.time()
            was_speaking = is_speaking()
            set_gui_state("listening")
            command = Command()
            if command is None: 
                set_gui_state("rest")
                continue

            command = command.strip()
            if not command:
                continue

            has_alfred = bool(re.match(r"^alfred\b", command, re.IGNORECASE))

            # Case 1: Starts with 'alfred' -> highest priority!
            if has_alfred:
                if message_queue:
                    logger.info(f"Flush message queue ({len(message_queue)} items) due to high-priority 'alfred' command.")
                    message_queue.clear()

                if was_speaking or is_speaking():
                    logger.info("Interrupt keyword 'alfred' detected while speaking. Stopping speech immediately.")
                    stop_speaking()
                    interrupted_speech = True

                # Strip leading 'alfred' prefix
                command = re.sub(r"^alfred\s*[,:]?\s*", "", command, flags=re.IGNORECASE).strip()
                if not command:
                    continue

                logger.info(f"High-priority query received: {command}")
                handle_query_execution(command, q_start)
                continue

            # Case 2: Does not start with 'alfred' -> push to message queue
            logger.info(f"Command does not start with 'alfred'. Adding to queue: '{command}'")
            message_queue.append(command)

            # If assistant is not speaking, immediately handle next item in queue
            if not is_speaking():
                next_cmd = message_queue.popleft()
                logger.info(f"Proceeding immediately with queue query: '{next_cmd}'")
                handle_query_execution(next_cmd, q_start)
                
        except Exception as loop_error:
            logger.error(f"Error inside command handler loop: {loop_error}", exc_info=True)


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        import traceback
        
        err_msg = traceback.format_exc()
        logger.critical(f"ALFRED crashed with error: {error}", exc_info=True)
        print("An error occurred:")
        print(err_msg)
