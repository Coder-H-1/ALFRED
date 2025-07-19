
from FILES.utils import butler_response , get_greeting
from FILES.commands import process_command
from FILES.reminder import start_background_reminder_thread
from FILES.task_listener import listen_command
from FILES.speaker import speak 

import os, sys

COMMAND_INPUT = False

def Command() -> str:
    if COMMAND_INPUT:
        command = str(input(">> ")).lower()
    
    else:
        command = listen_command()  
        # command = str(input(">> ")).lower()  # to debug 

    return command

def main():
    global COMMAND_INPUT
    speak("System is now fully operational.")
    os.system("cls")
    speak(get_greeting())

    while True:
        command = Command()

        if "switch command" in command:
            if COMMAND_INPUT:
                COMMAND_INPUT = False
            else:
                COMMAND_INPUT = True
                
            continue
        
        if "restart yourself" in command or "restart yourselves" in command or "restart your self" in command or "restart your" in command:
            os.startfile("Main.py")
            sys.exit()

        if "exit" in command or "goodbye" in command or "bye alfred" in command:
            response = butler_response("Bye alfred. Meet you soon.")
            speak(response)
            break

        if command:
            system_action = process_command(command)
            if system_action:
                speak(system_action)
            else:
                response = butler_response(command)
                speak(response)

if __name__ == "__main__":
    start_background_reminder_thread()

    main()
