
from FILES.utils import Responder , get_greeting, MEMORY
from FILES.commands import process_command
from FILES.reminder import start_background_reminder_thread
from FILES.util_functions import listen_command, speak
from FILES.intent import INTENT
import os, sys

COMMAND_INPUT = False  # True -> listen_command() ; False -> CLI (Command Line Interface) 

def Command() -> str:  ### Changes COMMAND_INPUT VALUES [True/False]
    "Takes command from specified source"
    if COMMAND_INPUT:
        command = str(input(">> ")).lower()
    else:
        command = listen_command()

    return command

def main() -> None:
    global COMMAND_INPUT

    speak("System is now fully operational.")
    os.system("title ALFRED")
    os.system("cls")
    speak(get_greeting())

    while True:
        command = Command()
        intent = INTENT()
        if command==None:
            continue
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
            MEMORY.session_end()
            speak(Responder("good day alfred. Now you may close yourself."))
            sys.exit()
            
        
        system_action = process_command(command)
        if system_action:
            speak(system_action)
            MEMORY.add_to_history(command, system_action)
        else:
            speak( Responder(command) ) 


if __name__ == "__main__":
    start_background_reminder_thread()
    try:
        main()
    except Exception as error:
        print(error)
