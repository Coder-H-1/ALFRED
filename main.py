from FILES.utils import Responder, get_greeting, MEMORY
from FILES.commands import process_command
from FILES.util_functions import listen_command, speak, stop_speaking, is_speaking
from FILES.plugin_host import start_plugin_listener, match_dynamic_command
from FILES.gui_controller import (
    init_config, set_query_active, show_answer, show_logs, 
    add_function_call, show_data, hide_all, hide_transient_boxes, 
    set_input_mode, read_gui_command
)
from FILES.log_compressor import compress_all_rotated_logs
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import LatencyRecorder
import os
import sys
import subprocess
import atexit
import time
import webbrowser
import re
import gc
from dotenv import load_dotenv
import version


# Load .env file at startup
load_dotenv()

logger = get_logger(__name__)

def filter_speech(text):
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    return text.strip()

COMMAND_INPUT = False # if True then we can type the command else it will listen the command

def start_gui_server():
    logger.info("Starting Next.js GUI Dev Server...")
    # Use lowercase 'gui' as folder name
    gui_path = os.path.join(os.path.dirname(__file__), "gui")
    
    # Make sure we use shell=True on windows
    try:
        process = subprocess.Popen(
            "npm run dev", 
            cwd=gui_path, 
            shell=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        logger.info("GUI Server spawned successfully.")
    except Exception as e:
        logger.error(f"Failed to spawn GUI Server: {e}", exc_info=True)
        raise

    def cleanup():
        logger.info("Terminating GUI Server...")
        try:
            process.terminate()
        except Exception as e:
            logger.error(f"Failed to terminate GUI Server process: {e}")
        
    atexit.register(cleanup)
    atexit.register(compress_all_rotated_logs)


def Command() -> str:
    if COMMAND_INPUT:
        set_input_mode(True)
        logger.debug("Waiting for GUI input...")
        while True:
            cmd = read_gui_command()
            if cmd:
                logger.info(f"Received GUI command: '{cmd}'")
                set_input_mode(False)
                return cmd.lower()
            time.sleep(0.5)
    else: 
        command = listen_command()
        return command

def main():
    global COMMAND_INPUT
    
    logger.info(f"Starting {version.PROJECT_NAME}")
    
    # Reset GUI layout and state on startup
    data_dir = os.path.join(os.path.dirname(__file__), "Data")
    for file_name in ["config.json", "layout_state.json"]:
        file_path = os.path.join(data_dir, file_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleared GUI state file: {file_name}")
            except Exception as e:
                logger.warning(f"Failed to clear GUI file {file_name}: {e}")
                
    init_config()
    start_gui_server()
    
    # Initialize latency recorder and log startup
    latency = LatencyRecorder()
    latency.startup_record()
    
    # Open GUI in default browser
    gui_url = f"http://localhost:{version.GUI_PORT}"
    logger.info(f"Opening GUI URL in browser: {gui_url}")
    webbrowser.open(gui_url)
    
    time.sleep(1.5)
    
    try:
        import keyboard
        keyboard.press_and_release('f11')
    except Exception as e:
        logger.warning(f"Failed to toggle fullscreen (f11) on launch: {e}")
        
    speak("System is now fully operational.")
    os.system(f"title {version.PROJECT_NAME}")
    os.system("cls")
    
    speak(get_greeting())
    start_plugin_listener()

    interrupted_speech = False

    while True:
        try:
            q_start = time.time()
            was_speaking = is_speaking()
            command = Command()
            if command is None: 
                continue

            command = command.strip()
            if not command:
                continue

            # In-between voice interrupt check
            voice_active = was_speaking or is_speaking()
            has_alfred = bool(re.match(r"^alfred\b", command, re.IGNORECASE))

            if voice_active:
                if not has_alfred:
                    logger.debug("Speech active and command does not start with 'alfred'. Ignoring audio.")
                    continue
                else:
                    logger.info("Interrupt keyword 'alfred' detected while speaking. Stopping speech immediately.")
                    stop_speaking()
                    interrupted_speech = True

            # Strip leading 'alfred' prefix for uniform command matching
            if has_alfred:
                command = re.sub(r"^alfred\s*[,:]?\s*", "", command, flags=re.IGNORECASE).strip()

            if not command:
                continue

            set_query_active(True)
            show_logs(f"Query received: {command}")
            add_function_call("Command Listener")
            add_function_call("Intent Matcher")

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
            if any(command == kw or command.startswith(kw) for kw in continue_keywords):
                show_logs("Continue command received. Recalling previous speech from Long Term Memory...")
                add_function_call("LTM Recall")
                prev_speech = MEMORY.get_last_assistant_response()
                if prev_speech:
                    clean_prev_speech = filter_speech(prev_speech)
                    show_answer(clean_prev_speech)
                    speak(clean_prev_speech)
                    show_logs("Resynthesised and speaking previous speech from LTM.")
                    hide_transient_boxes()
                else:
                    speak("I have no previous speech in memory to continue, sir.")
                interrupted_speech = False
                continue

            # If user does not say continue:
            # Stop synthesizing previous text and clean memory using garbage collector
            if interrupted_speech:
                stop_speaking()
                gc.collect()
                interrupted_speech = False

            if "switch command" in command:
                COMMAND_INPUT = not COMMAND_INPUT
                logger.info(f"Switched COMMAND_INPUT mode to: {COMMAND_INPUT}")
                set_query_active(False)
                continue
            
            if any(kw in command for kw in ("restart yourself", "restart yourselves", "restart your self", "restart your")):
                logger.info("Restart command received. Restarting main.py process...")
                os.startfile("main.py")
                sys.exit()

            if any(kw in command for kw in ("exit", "goodbye", "bye alfred", "shutdown yourself", "you may sleep now")):
                logger.info("Exit command received. Ending memory session and exiting.")
                MEMORY.session_end()
                speak(Responder("good day alfred. Now you may close yourself."))
                sys.exit()
                
            show_logs("Checking for dynamic plugins...")
            plugin_result = match_dynamic_command(command)
            if plugin_result:
                show_logs("Dynamic plugin matched successfully.")
                add_function_call("match_dynamic_command")
                clean_plugin_result = filter_speech(plugin_result)
                show_answer(clean_plugin_result)
                speak(clean_plugin_result)
                MEMORY.add_to_history(command, plugin_result)
                show_logs("Added interaction to memory.")
                hide_transient_boxes()
                continue

            show_logs("No dynamic plugin matched. Checking system actions...")
            system_action = process_command(command)
            if system_action:
                show_logs("System action matched successfully.")
                add_function_call("process_command")
                
                keep_ui = False
                if "[KEEP_UI]" in str(system_action):
                    keep_ui = True
                    system_action = str(system_action).replace("[KEEP_UI]", "").strip()

                clean_system_action = filter_speech(system_action)
                show_answer(clean_system_action)
                speak(clean_system_action)
                MEMORY.add_to_history(command, system_action)
                show_logs("Added interaction to memory.")
                
                if not keep_ui:
                    hide_transient_boxes()
            else:
                show_logs("No system action matched. Falling back to default Responder...")
                add_function_call("Responder")
                response = Responder(command)
                clean_response = filter_speech(response)
                show_answer(clean_response)
                speak(clean_response) 
                show_logs("Response generated and spoken.")
                hide_transient_boxes()
            
            # Record latency for this command cycle
            q_end = time.time()
            latency.record(
                source="main.command_loop",
                query_length=len(command) if command else 0,
                query_received_at=q_start,
                output_at=q_end
            )
                
        except Exception as loop_error:
            logger.error(f"Error inside command handler loop: {loop_error}", exc_info=True)


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        import traceback
        from FILES.gui_controller import show_error
        
        err_msg = traceback.format_exc()
        logger.critical(f"ALFRED crashed with error: {error}", exc_info=True)
        print("An error occurred:")
        print(err_msg)
        
        try:
            show_error(err_msg)
            time.sleep(10) # Give the user time to read the error before exiting
        except Exception as e:
            logger.error(f"Failed to display GUI crash error page: {e}")
            pass
