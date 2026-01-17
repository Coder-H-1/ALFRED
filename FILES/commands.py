from FILES.util_functions       import EDIT,  listen_command, speak
from FILES.utils                import clear_Memory, get_date, get_time
from FILES.model_manager        import ModelManager, MODELS

from FILES.reminder  import (
    set_reminder, 
    parse_spoken_time, 
    cancel_reminder,
    list_reminders
    )
from FILES.system_control import (
    mute_volume, 
    adjust_brightness,
    adjust_volume, 
    set_brightness,
    set_volume
    )
from FILES.youtube_player import (
    play_youtube_audio, 
    stop_youtube_audio,
    VOLUME_YOUTUBE,
    set_volume_youtube
    )


import keyboard
import os
import re
import webbrowser

model_Manager = ModelManager() 
                # .load_model(model_path:str, name:str, context_len: int) 
                # .unload_model() 
                # .prompt(prompt:str, max_token:int)

def Open_application(command:str) -> str:
    pass

def process_command(command:str, Intent:str) -> str:  ### Executes commands after looking for certain keyword
    "Executes command with certain keyword"

    global VOLUME_YOUTUBE
    
    command = EDIT(
        str(command), FROM_str=["open", "start", "close" , "end"], TO_str=["$", "$" , "&" , "&"]
        ).replace()
    
    

    if "remind me" in command:
        match = re.search(r"remind me to (.+?) in (.+)", command)
        if match==None:
            match = re.search(r"remind me to (.+?) at (.+)", command)

        if match:
            task = match.group(1).strip()
            time_text = match.group(2).strip()

            alarm_time = parse_spoken_time(time_text)

            if alarm_time:
                set_reminder(task, alarm_time)
                return f"Reminder noted: '{task}' for {alarm_time}, sir."
            else:
                return "I couldn't understand the time, sir."
        else:
            return "Might I ask when to remind you, sir?"

    elif "set alarm for" in command:
        match = re.search(r"set alarm for (.+)", command)
        if match:
            time_text = match.group(1).strip()
            alarm_time = parse_spoken_time(time_text)
            if alarm_time:
                set_reminder("your alarm", alarm_time)
                return f"Alarm set for {alarm_time.strftime('%I:%M %p')}, sir."
            else:
                return "Could you repeat the time for the alarm, sir?"

    elif "cancel reminder" in command or "cancel alarm" in command:
        match = re.search(r"cancel (?:reminder|alarm) (.+)", command)
        if match:
            target = match.group(1).strip()
            cancel_reminder(target)
            return f"I've looked into cancelling '{target}', sir."
        else:
            return "Could you please specify which reminder or alarm to cancel, sir?"

    elif "list reminders" in command or "what reminders" in command:
        return list_reminders()
    
    elif "play from youtube" in command or "play on youtube" in command or "play" in command or "on youtube" in command:
        parts = command.split("play", 1)
        if len(parts) > 1:
            query = parts[1].replace("from youtube", "").replace("on youtube", "").strip()
            if query:
                play_youtube_audio(query)
                return "Done."
            else:
                return ("Could you please repeat the song, sir?")
        else:
            return ("Please specify what you'd like to play, sir.")

    elif "stop youtube" in command or "stop music" in command:
        return stop_youtube_audio()

    ################################################################################################

    # NOTE: This code will only work for fine-tuned Qwen2.5-0.5-Instruct model     ; These functions were self trained by me 
    # IF: you want to run these commands remove these elif statements -> goes to main ChatModel (heavy).      

    elif "linux command" in command:
        model_Manager.load_model(MODELS["linux command"], name="linux-commands", context_len=(len(command)+25))
        answer = model_Manager.prompt(prompt=command, max_token=200)
        model_Manager.unload_model()
        return answer 

    elif "linux tool" in command:
        model_Manager.load_model(MODELS["linux tool"], name="linux-tools", context_len=(len(command)+25))
        answer = model_Manager.prompt(prompt=command, max_token=200)
        model_Manager.unload_model()
        return answer

    elif "quote" in command:
        model_Manager.load_model(MODELS["quote"], name="quotes" , context_len=(len(command)+25))        
        answer = model_Manager.prompt(prompt=command, max_token=250)
        model_Manager.unload_model()
        return answer
    
    ################################################################################################

    elif "youtube volume" in command:
        global VOLUME_youtube
        if "set" in command:
            for word in command.split():
                if word.isdigit():
                    VOLUME_YOUTUBE = int(word)
                    set_volume_youtube()
                    return f"Youtube's volume is now set to : {VOLUME_YOUTUBE}"
                else:
                    return "Couldn't set volume could you please repeat the command, sir."

        if "increase" in command:
            VOLUME_YOUTUBE += 10
            set_volume_youtube()
            return f"Youtube volume is now set to : {VOLUME_youtube} %"
        elif "decrease" in command:
            VOLUME_YOUTUBE -= 10
            set_volume_youtube()
            return f"Youtube volume is now set to : {VOLUME_youtube} %"

    elif "volume" in command:
        if "mute" in command:
            return mute_volume()
        elif "increase" in command:
            return adjust_volume("increase")
        elif "decrease" in command:
            return adjust_volume("decrease")
        elif "set" in command:
            for word in command.split():
                if word.isdigit():
                    return set_volume(int(word))

    elif "brightness" in command:
        if "increase" in command:
            return adjust_brightness("increase")
        elif "decrease" in command:
            return adjust_brightness("decrease")
        elif "set" in command:
            for word in command.split():
                if word.isdigit():
                    return set_brightness(int(word))

    elif "time" in command and "what" in command:
        return get_time()

    elif "date" in command or "day" in command: 
        if "what" in command: return get_date()
    
    elif "$ taskmanager" in command or "$ task manager" in command or "$ resource monitor" in command:
        keyboard.press_and_release("ctrl + shift + esc")
        return "Opening Task manager"
    elif "& taskmanager" in command or "& task manager" in command or "& resource monitor" in command:
        os.system()
        return "Closing Task manager"
    
    elif "$ note pad" in command or "$ notepad" in command:
        os.system("start notepad")
        return "Opening Notepad."
    elif "& note pad" in command or "& notepad" in command:
        os.system(f"taskkill /f /im notepad.exe")
        return "Closed Notepad"

    elif "$ cmd" in command or "$ command prompt" in command:
        os.system("start cmd")
        return "Opening Command Prompt."
    elif "& cmd" in command or "& command prompt" in command:
        os.system(f"taskkill /f /im cmd.exe")
        return "Closed all Command Prompt"

    elif "$ system information" in command:
        os.system("start dxdiag")
        return "Opening System Information."
    elif "& system information" in command:
        os.system("taskkill /f /im dxdiag.exe")
        return "Closed system information"
    
    elif "clear screen" in command or "clear terminal" in command:
        os.system("cls")
        return "Cleared Screen"
    
    elif "go to desktop" in command or "go to main screen" in command:
        keyboard.press_and_release("win + d")
        return "You are on Desktop now."

    elif "$ code" in command: 
        os.system("code")
        return "Opening VS CODE"    
    elif "& code" in command:
        os.system("taskkill /f /im code.exe")
        return "Closed VS CODE"
    
    elif "$ chrome" in command:
        os.system("start chrome")
        return "Opening Chrome."
    elif "& chrome" in command:
        os.system("taskkill /f /im chrome.exe")
        return "Closed Chrome"

    elif "$ firefox" in command or "$ browser" in command:
        os.system("start firefox.exe")
    elif "& firefox" in command or "$ browser" in command:
        os.system(f"taskkill /f /im firefox.exe")
        return "Closed Firefox"

    elif "$ calculator" in command:
        os.system("start calc")
        return "Opening Calculator."
    elif "& calculator" in command:
        os.system("taskkill /f /im calc.exe")
        return "Closed Calculator"

    elif "$ workplace" in command or "$ workspace" in command or "$ work place" in command or "$ work space" in command:
        webbrowser.open_new_tab("https://www.chatgpt.com")
        webbrowser.open_new_tab("https://github.com/Coder-H-1")
        os.system(f"code {os.getcwd()}")
        return "Opening Workspace."
    
    elif "& workplace" in command or "& workspace" in command or "& work place" in command or "& work space" in command:
        os.system("taskkill /f /im code.exe")
        return "Closed Workspace"

    elif "$ whatsapp" in command or "$ chats" in command:
        os.system("start shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
        return "Opening WhatsApp"
    elif "& whatsapp" in command:
        os.system("taskkill /f /im whatsapp.exe")
        return "Closed WhatsApp"
    
    elif "$ advanced system settings" in command or "$ advance settings" in command or "$ system properties" in command:
        os.system("start sysdm.cpl")
        return "Opening Advanced System Settings"

    elif "$ computer settings" in command:
        keyboard.press_and_release("win + i")
        return "Opening Settings"

    elif "$ youtube music" in command:
        os.system("start chrome.exe https://music.youtube.com")
        return "Opening Youtube Music in browser"

    elif "$ stack overflow" in command:
        webbrowser.open_new_tab("stackoverflow.com")
        return "Opening stackoverflow"

    elif "$ google" in command or "$ search" in command:
        webbrowser.open_new_tab("google.com")
        return "Opening Google"
    
    elif "$ chatter" in command or "$ chatgpt" in command:
        webbrowser.open_new_tab("chatgpt.com")
        return "Opening ChatGPT"

    elif "shutdown computer" in command or "shut down the computer" in command or "shutdown system" in command or "shutdown the system" in command:
        os.system("shutdown /s /t 1")
        return "Shutting down the system now."

    elif "restart computer" in command or "restart the computer" in command or "restart system" in command or "restart the system" in command:
        os.system("shutdown /r /t 1")
        return "Restarting your machine, sir."
    
    elif "clear memory" in command or "forget everything" in command or "clear your memory" in command:
        clear_Memory()
        return "Cleared Memory at your command"

    elif "search file" in command or "find file" in command or "serge file" in command:
        parts = command.split("file", 1)
        if len(parts) > 1:
            query = parts[1].strip()
            return search_files(query)
        else:
            return "Might I ask which file you’re looking for, sir?"
        
    else: 
        return None

def search_files(filename: str, search_path="C:\\", is_commanded:bool=False, to_find:int=5) -> str:    ### Searches for required file in 'search_path' = 'C:\\' 
    results = []
    query = filename.lower()

    if is_commanded!=True: speak("Allow me a moment, sir.")

    for root, dirs, files in os.walk(search_path):
        print(f"{str(root).replace("\n", "")} \r")
        if "C:\\Windows\\WinSxS" in root:
            continue
        else:
            for file in files:
                if query in file.lower():
                    results.append(os.path.join(root, file))
                    if len(results) >= to_find:
                        break
            if len(results) >= to_find:
                break

        

    if results:
        if is_commanded:
            for idx, path in enumerate(results, 1):
                return path                   
        else:    
            speak("I found the following matches, sir:")
            for idx, path in enumerate(results, 1):
                print(f"{idx}. 📁 {path}")

            speak("Shall I open the first result for you?")
            confirmation:str = listen_command()
             

            if "cancel" in confirmation or "stop" in confirmation or confirmation == None:
                return "Understood, I won’t open anything."

            if "yes" in confirmation or "open" in confirmation:
                try:
                    os.startfile(results[0])
                    return "Opening the file now."
                except Exception as e:
                    return f"I'm afraid I couldn’t open it. The error was: {e}"

            return "Very well, I shall await further instructions."
    else:
        return "I'm afraid I found no matching files, sir."


