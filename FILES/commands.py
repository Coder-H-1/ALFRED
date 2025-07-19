from FILES.text_editor import EDIT
from FILES.utils import clear_Memory, get_date, get_time
from FILES.reminder import set_reminder, parse_spoken_time, cancel_reminder,list_reminders
from FILES.system_control import mute_volume, adjust_brightness, adjust_volume, set_brightness,set_volume
from FILES.youtube_player import play_youtube_audio, stop_youtube_audio, VOLUME_youtube,set_volume_youtube

from FILES.task_listener import listen_command
from FILES.speaker import speak

import keyboard
import os
import re
import webbrowser


def process_command(command:str):
    command = EDIT(command, ["open", "start", "close" , "end"], ["$", "$" , "&" , "&"]).replace()
    
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
            else:
                return ("Could you please repeat the song, sir?")
        else:
            return ("Please specify what you'd like to play, sir.")

    elif "stop youtube" in command or "stop online music" in command:
        return stop_youtube_audio()

    elif "youtube volume" in command:
        global VOLUME_youtube
        command = command.replace("youtube volume" , "")
        if "set" in command:
            for word in command.split():
                if word.isdigit():
                    VOLUME_youtube = int(word)
                    set_volume_youtube()
                    return f"Youtube's volume is now set to : {VOLUME_youtube}"
                else:
                    return "Couldn't set volume could you please repeat the command, sir."

        if "increase" in command:
            VOLUME_youtube += 10
            set_volume_youtube()
            return f"Youtube volume is now set to : {VOLUME_youtube} %"
        elif "decrease" in command:
            VOLUME_youtube -= 10
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

    elif "time" in command:
        return get_time()

    elif "date" in command or "day" in command:
        return get_date()
    
    elif "$ taskmanager" in command or "$ task manager" in command or "$ resource monitor" in command:
        keyboard.press_and_release("ctrl + shift + esc")
        return "Opening Task manager"

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
    
    elif "clear screen" in command or "clear terminal" in command:
        os.system("cls")
        return "Cleared Screen"
    
    elif "go to desktop" in command or "go to main screen" in command:
        keyboard.press_and_release("win + d")
        return "You are on Desktop now."

    elif "$ chrome" in command:
        os.system("start chrome")
        return "Opening Chrome."
    elif "& chrome" in command:
        os.system("taskkill /f /im chrome.exe")

    elif "$ firefox" in command or "$ browser" in command:
        os.system("start firefox.exe")
    elif "& firefox" in command or "$ browser" in command:
        os.system(f"taskkill /f /im firefox.exe")

    elif "$ calculator" in command:
        os.system("start calc")
        return "Opening Calculator."
    elif "& calculator" in command:
        os.system("taskkill /f /im calc.exe")

    elif "$ workplace" in command or "$ workspace" in command or "$ work place" in command or "$ work space" in command:
        webbrowser.open_new_tab("https:\\www.chatgpt.com")
        os.system(f"code {os.getcwd()}")
        return "Opening Workspace."
    elif "& workplace" in command or "& workspace" in command or "& work place" in command or "& work space" in command:
        os.system("taskkill /f /im code.exe")

    elif "$ whatsapp" in command:
        os.system("start shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
        return "Opening WhatsApp"
    elif "& whatsapp" in command:
        os.system("taskkill /f /im whatsapp.exe")
    
    elif "$ advance system settings" in command or "$ advance settings" in command or "$ system properties" in command:
        os.system("start sysdm.cpl")

    elif "check disk for errors" in command:
        os.system(f"chkdsk")

    elif "$ computer settings" in command:
        keyboard.press_and_release("win + i")
        return "Opening Settings"

    elif "$ stack overflow" in command:
        webbrowser.open_new_tab("stackoverflow.com")
        return "Opening stackoverflow.com"

    elif "$ google" in command:
        webbrowser.open_new_tab("google.com")
        return "Opening Google.com"
    
    elif "$ chatter" in command:
        webbrowser.open_new_tab("chatgpt.com")
        return "Opening ChatGPT.com"

    elif "shutdown computer" in command or "shut down the computer" in command:
        os.system("shutdown /s /t 1")
        return "Shutting down the system now."

    elif "restart computer" in command:
        os.system("shutdown /r /t 1")
        return "Restarting your machine, sir."
    
    elif "clear memory" in command or "forget everything" in command:
        clear_Memory()
        return "Cleared Memory at your command"

    elif "search file" in command or "find file" in command or "serge file" in command:
        parts = command.split("file", 1)
        if len(parts) > 1:
            query = parts[1].strip()
            return search_files(query)
        else:
            return "Might I ask which file you’re looking for, sir?"
        
    else: return None


def search_files(query: str, search_path="C:\\") -> str:
    results = []
    query = query.lower()

    speak("Allow me a moment to search, sir.")

    for root, dirs, files in os.walk(search_path):
        print(dirs)
        for file in files:
            if query in file.lower():
                results.append(os.path.join(root, file))
                if len(results) >= 5:
                    break
        if len(results) >= 5:
            break

    if results:
        speak("I found the following matches, sir:")
        for idx, path in enumerate(results, 1):
            print(f"{idx}. 📁 {path}")

        speak("Shall I open the first result for you?")
        confirmation = listen_command()

        if "cancel" in confirmation or "stop" in confirmation:
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


