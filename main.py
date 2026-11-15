from FILES.startup import (
    os,
    sys,
    time,
    re,
    gc,
    deque,
    version,
    logger,
    initialize_system,
    set_gui_state,
    close_gui,
    listen_command,
    speak,
    stop_speaking,
    is_speaking,
    Responder,
    MEMORY,
    process_command,
    match_dynamic_command,
)

COMMAND_INPUT = True  # False: listen audio command, True: console text input


def filter_speech(text):
    """Strip parenthesis and asterisks/emojis from speech output."""
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    return text.strip()


def Command() -> str:
    """Acquires user command either from console input or speech audio."""
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

    # Execute all startup initializations, checks, and configurations
    startup_data = initialize_system()
    latency = startup_data["latency"]

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
        target_speech = None
        memory_entry = None

        plugin_result = match_dynamic_command(command_text)
        if plugin_result:
            logger.info("Dynamic plugin matched successfully.")
            target_speech = filter_speech(str(plugin_result).replace("[KEEP_UI]", "").strip())
            memory_entry = plugin_result
        else:
            system_action = process_command(command_text)
            if system_action:
                logger.info("System action matched successfully.")
                target_speech = filter_speech(str(system_action).replace("[KEEP_UI]", "").strip())
                memory_entry = system_action
            else:
                logger.info("No system action matched. Falling back to default Responder...")
                response = Responder(command_text)
                target_speech = filter_speech(response)
                memory_entry = response

        # Record query-to-response latency before speaking
        q_end = time.time()
        q_len = len(command_text) if command_text else 0
        resp_len = len(target_speech) if target_speech else 0
        latency.record(
            source="QUERY_RESPONSE",
            query_length=q_len,
            response_length=resp_len,
            query_received_at=q_start,
            output_at=q_end,
        )

        # Now speak response
        if target_speech:
            set_gui_state("work")
            speak(target_speech)
            if memory_entry:
                MEMORY.add_to_history(command_text, memory_entry)

    while True:
        try:
            # 0. Check background research / tool completions
            try:
                from MCP.tools.research_tools import pop_research_notification
                bg_note = pop_research_notification()
                if bg_note and not is_speaking():
                    logger.info(f"Announcing completed background research: '{bg_note}'")
                    set_gui_state("work")
                    speak(bg_note)
                    set_gui_state("rest")
            except (ImportError, Exception):
                pass

            # 1. Process queued commands if assistant is idle
            if message_queue and not is_speaking():
                next_cmd = message_queue.popleft()
                logger.info(f"Processing next query from queue ({len(message_queue)} remaining): '{next_cmd}'")
                handle_query_execution(next_cmd)
                continue

            # 2. Check speaking state before listening
            was_speaking = is_speaking()
            if not was_speaking:
                set_gui_state("listening")

            q_start = time.time()
            command = Command()
            if command is None:
                if not is_speaking():
                    set_gui_state("rest")
                continue

            command = command.strip()
            if not command:
                if not is_speaking():
                    set_gui_state("rest")
                continue

            has_alfred = bool(re.match(r"^alfred\b", command, re.IGNORECASE))

            # Case 1: Starts with 'alfred' -> highest priority! Interrupt ongoing speech!
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
                    set_gui_state("rest")
                    continue

                logger.info(f"High-priority query received: {command}")
                handle_query_execution(command, q_start)
                continue

            # Case 2: Does not start with 'alfred'
            # If assistant is speaking right now, push to queue so we don't interrupt ongoing speech
            if is_speaking():
                logger.info(f"Assistant is speaking. Adding non-alfred command to queue: '{command}'")
                message_queue.append(command)
                continue

            # If assistant is idle, process immediately
            logger.info(f"Processing command: '{command}'")
            handle_query_execution(command, q_start)

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
