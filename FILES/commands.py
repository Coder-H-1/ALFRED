from FILES.util_functions import multi_replace, search_files
from FILES.utils import clear_Memory, get_date, get_time, Responder
from FILES.model_manager import ModelManager, MODELS
from FILES.long_term_memory import LongTermMemory
from FILES.gui_controller import move_window, pin_window, set_video_control, show_data, hide_all, hide_transient_boxes
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

LTM = LongTermMemory()

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
from FILES.resource_monitor import format_stats_string, get_system_stats


import keyboard
import os
import re
import webbrowser
import requests
import base64
import wikipedia

model_Manager = ModelManager() 

BOX_MAPPING = {
    "answer": "answerBox", 
    "response": "answerBox", 
    "preview": "showBox", 
    "show": "showBox", 
    "log": "logs", 
    "logs": "logs", 
    "process": "functionCalls"
}

ZONE_MAPPING = {
    "focus": "focus", 
    "active": "active", 
    "passive": "passive", 
    "rapid": "rapid"
}

APP_REGISTRY = {
    "note pad":         {"open": "start notepad", "process": "notepad.exe", "name": "Notepad"},
    "notepad":          {"open": "start notepad", "process": "notepad.exe", "name": "Notepad"},
    "cmd":              {"open": "start cmd", "process": "cmd.exe", "name": "Command Prompt"},
    "command prompt":   {"open": "start cmd", "process": "cmd.exe", "name": "Command Prompt"},
    "system information":{"open": "start dxdiag", "process": "dxdiag.exe", "name": "System Information"},
    "code":             {"open": f"antigravity-ide.exe {os.getcwd()}", "process": "antigravity-ide.exe", "name": "Antigravity IDE"},
    "chrome":           {"open": "start chrome", "process": "chrome.exe", "name": "Chrome"},
    "firefox":          {"open": "start firefox.exe", "process": "firefox.exe", "name": "Firefox"},
    "browser":          {"open": "start firefox.exe", "process": "firefox.exe", "name": "Firefox"},
    "calculator":       {"open": "start calc", "process": "calc.exe", "name": "Calculator"},
}

WEB_REGISTRY = {
    "youtube music":    {"url": "https://music.youtube.com", "name": "Youtube Music in browser"},
    "stack overflow":   {"url": "https://www.stackoverflow.com", "name": "stackoverflow"},
    "google":           {"url": "https://www.google.com", "name": "Google"},
    "search":           {"url": "https://www.google.com", "name": "Google"},
    "chatter":          {"url": "https://www.chatgpt.com", "name": "ChatGPT"},
    "chatgpt":          {"url": "https://www.chatgpt.com", "name": "ChatGPT"},
}

@track_latency("commands.close_application_through_cmd")
def close_application_through_cmd(process_name:str, return_response:str = None) -> str:
    logger.info(f"Attempting to close process: {process_name}")
    if " " in process_name:
        process_name = process_name.split(" ")[-1]
    os.system(f"taskkill /f /im {process_name}")
    return return_response or f"Closed {process_name}"

@track_latency("commands.process_command")
def process_command(command:str, Intent:str=None) -> str:
    logger.info(f"Processing command: '{command}' with Intent: '{Intent}'")
    global VOLUME_YOUTUBE
    
    command = multi_replace(str(command), {"open": "$", "start": "$", "close": "&", "end": "&"})
    
    # Wikipedia/Online Search Integration
    if command.startswith("who is ") or command.startswith("what is ") or command.startswith("tell me about "):
        query = command.replace("who is ", "").replace("what is ", "").replace("tell me about ", "").strip()
        if query:
            logger.info(f"Processing search/wikipedia query for: '{query}'")
            
            # 1. Try online search
            try:
                from FILES.web_search_extractor import extract_web_data
                search_res = extract_web_data(query)
                if search_res and not search_res.get("error") and search_res.get("details"):
                    details = search_res.get("details", [])
                    combined = " ".join([d.strip() for d in details if d.strip()][:2])
                    if combined:
                        logger.info("Online search via backend succeeded.")
                        images = search_res.get("images", [])
                        if images:
                            show_data(images[:3])
                        return combined + " [KEEP_UI]"
            except Exception as e:
                logger.warning(f"Online backend search failed: {e}")

            # 2. Fallback to local Wikipedia library search
            try:
                temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Data", "temp_images")
                os.makedirs(temp_dir, exist_ok=True)
                
                for f in os.listdir(temp_dir):
                    try:
                        os.remove(os.path.join(temp_dir, f))
                    except Exception as e:
                        logger.debug(f"Failed to remove temp image {f}: {e}")
                
                summary = wikipedia.summary(query, sentences=2)
                page = wikipedia.page(query, auto_suggest=False)
                
                images_b64 = []
                for img_url in page.images:
                    if img_url.lower().endswith(('.jpg', '.jpeg', '.png')) and not "svg" in img_url.lower():
                        try:
                            res = requests.get(img_url, timeout=5)
                            if res.status_code == 200:
                                filename = os.path.basename(img_url).split("?")[0]
                                filepath = os.path.join(temp_dir, filename)
                                with open(filepath, 'wb') as f:
                                    f.write(res.content)
                                
                                ext = "jpeg" if filename.lower().endswith(".jpg") else "png"
                                b64_data = base64.b64encode(res.content).decode('utf-8')
                                images_b64.append(f"data:image/{ext};base64,{b64_data}")
                                
                                if len(images_b64) >= 3:
                                    break
                        except Exception as e:
                            logger.debug(f"Failed to download image {img_url}: {e}")
                
                if images_b64:
                    show_data(images_b64)
                    
                logger.info("Wikipedia library query succeeded.")
                return summary + " [KEEP_UI]"
            except Exception as e:
                logger.warning(f"Wikipedia library search failed: {e}. Falling back to local LLM.")
                # Returning None forces main.py to fall back to local LLM responder
                return None

    # Zone & Window Movement Commands
    if "move window" in command or "move box" in command:
        words = command.split()
        box_name = None
        zone_name = None
        for w in words:
            if w in BOX_MAPPING: box_name = BOX_MAPPING[w]
            if w in ZONE_MAPPING: zone_name = ZONE_MAPPING[w]
        
        if box_name and zone_name:
            logger.info(f"Moving window {box_name} to {zone_name}")
            if move_window(box_name, zone_name):
                return f"Moved {box_name} to the {zone_name} zone, sir."
        return "I didn't quite catch which window to move where, sir."

    elif "pin window" in command or "pin box" in command:
        words = command.split()
        box_name = None
        for w in words:
            if w in BOX_MAPPING: box_name = BOX_MAPPING[w]
        
        if box_name:
            logger.info(f"Pinning window {box_name}")
            if pin_window(box_name, True):
                return f"Pinned {box_name}, sir."
        return "I didn't catch which window to pin."

    elif "unpin window" in command or "unpin box" in command:
        words = command.split()
        box_name = None
        for w in words:
            if w in BOX_MAPPING: box_name = BOX_MAPPING[w]
        
        if box_name:
            logger.info(f"Unpinning window {box_name}")
            if pin_window(box_name, False):
                return f"Unpinned {box_name}, sir."
        return "I didn't catch which window to unpin."
        
    elif "clean the gui" in command or "clear the screen" in command:
        logger.info("Clearing GUI screen")
        hide_all()
        return "The screen has been cleared, sir."

    elif "decompress logs" in command or "expand logs" in command:
        try:
            from FILES.log_compressor import decompress_log
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logs_dir = os.path.join(base_dir, "logs")
            count = 0
            if os.path.exists(logs_dir):
                for item in os.listdir(logs_dir):
                    if item.endswith(".compressed_logs"):
                        decompress_log(os.path.join(logs_dir, item))
                        count += 1
            if count > 0:
                return f"Successfully decompressed {count} log file(s), sir."
            else:
                return "No compressed log files were found in the logs directory, sir."
        except Exception as e:
            logger.error(f"Failed to decompress logs: {e}", exc_info=True)
            return f"Failed to decompress logs: {str(e)}"

    elif "compress logs" in command:
        try:
            from FILES.log_compressor import compress_all_rotated_logs
            compress_all_rotated_logs()
            return "Log compression process completed, sir."
        except Exception as e:
            logger.error(f"Failed to compress logs: {e}", exc_info=True)
            return f"Failed to compress logs: {str(e)}"

    elif "check weather outside" in command:
        try:
            api_key = os.getenv("OpenWeatherKey")
            if not api_key:
                return "No OpenWeatherKey found in environment variables, sir."
            
            logger.info("Fetching weather locally...")
            ip_info = requests.get("http://ip-api.com/json/", timeout=5).json()
            lat = ip_info.get("lat")
            lon = ip_info.get("lon")
            city = ip_info.get("city", "Unknown location")
            
            if lat and lon:
                url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
                res = requests.get(url, timeout=5).json()
                weather_data = {"weather": res, "city": city}
                prompt = f"The user wants to check the weather. The JSON data is {weather_data}. Answer the user based on this data."
                return Responder(prompt)
            else:
                return "Could not determine location coordinates, sir."
        except Exception as e:
            logger.error(f"Failed to check weather: {e}", exc_info=True)
            return f"Failed to check weather: {str(e)}"
            
    elif "could you repeat what you just said" in command or "repeat what you just said" in command or "repeat the answer" in command:
        try:
            logger.info("Recalling previous assistant response")
            output = LTM.print_memories(limit=2)
            lines = output.split('\n')
            for line in lines:
                if "ALFRED:" in line and "repeat" not in line.lower():
                    response = line.split("ALFRED:")[1].strip()
                    if response:
                        return response
            
            conn = LTM.get_db_connection()
            c = conn.cursor()
            c.execute('''
                SELECT content FROM memories 
                WHERE role = 'assistant' 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            row = c.fetchone()
            conn.close()
            if row:
                return row[0]
            
            return "I have no recent memory to repeat, sir."
        except Exception as e:
            logger.error(f"Error repeating answer: {e}", exc_info=True)
            return "I could not retrieve my previous answer, sir."
        
    # Video Playback Controls
    elif "video audio only" in command or "play audio only" in command:
        logger.info("Video audio only mode requested")
        set_video_control("audio_only")
        return "Video is now playing audio only, sir."
    elif "show video" in command or "enable video" in command:
        logger.info("Show video mode requested")
        set_video_control("show_video")
        return "Video visuals enabled, sir."
    elif "mute video" in command:
        logger.info("Mute video requested")
        set_video_control("mute")
        return "Video muted."
    elif "unmute video" in command:
        logger.info("Unmute video requested")
        set_video_control("unmute")
        return "Video unmuted."
    elif "rewind video" in command or "go back" in command:
        logger.info("Rewind video 10 seconds requested")
        set_video_control("rewind", 10)
        return "Rewound video."
    elif "forward video" in command or "skip ahead" in command:
        logger.info("Forward video 10 seconds requested")
        set_video_control("forward", 10)
        return "Forwarded video."
       
    if "play from youtube" in command or "play on youtube" in command or "on youtube" in command:
        parts = command.split("play", 1)
        if len(parts) > 1:
            query = parts[1].replace("from youtube", "").replace("on youtube", "").strip()
            if query:
                logger.info(f"YouTube play requested for query: '{query}'")
                return play_youtube_audio(query)
            else:
                return "Could you please repeat the song, sir?"
        else:
            return "Please specify what you'd like to play, sir."

    elif "stop youtube" in command or "stop music" in command:
        logger.info("Stopping YouTube music")
        return stop_youtube_audio()

    elif "youtube volume" in command:
        if "set" in command:
            for word in command.split():
                if word.isdigit():
                    VOLUME_YOUTUBE = int(word)
                    logger.info(f"Setting YouTube volume to {VOLUME_YOUTUBE}")
                    set_volume_youtube()
                    return f"Youtube's volume is now set to : {VOLUME_YOUTUBE}"
            return "Couldn't set volume could you please repeat the command, sir."

        if "increase" in command:
            VOLUME_YOUTUBE += 10
            logger.info(f"Increasing YouTube volume to {VOLUME_YOUTUBE}")
            set_volume_youtube()
            return f"Youtube volume is now set to : {VOLUME_YOUTUBE} %"
        elif "decrease" in command:
            VOLUME_YOUTUBE -= 10
            logger.info(f"Decreasing YouTube volume to {VOLUME_YOUTUBE}")
            set_volume_youtube()
            return f"Youtube volume is now set to : {VOLUME_YOUTUBE} %"

    elif "volume" in command:
        if "mute" in command:
            logger.info("Muting master volume")
            return mute_volume()
        elif "increase" in command:
            logger.info("Increasing master volume")
            return adjust_volume("increase")
        elif "decrease" in command:
            logger.info("Decreasing master volume")
            return adjust_volume("decrease")
        elif "set" in command:
            for word in command.split():
                if word.isdigit():
                    val = int(word)
                    logger.info(f"Setting master volume to {val}")
                    return set_volume(val)

    elif "brightness" in command:
        if "increase" in command:
            logger.info("Increasing master brightness")
            return adjust_brightness("increase")
        elif "decrease" in command:
            logger.info("Decreasing master brightness")
            return adjust_brightness("decrease")
        elif "set" in command:
            for word in command.split():
                if word.isdigit():
                    val = int(word)
                    logger.info(f"Setting master brightness to {val}")
                    return set_brightness(val)

    elif "time" in command and "what" in command:
        logger.info("Get current time requested")
        return get_time()

    elif "date" in command or "day" in command: 
        if "what" in command:
            logger.info("Get current date requested")
            return get_date()

    # Dynamic app opening/closing
    for app_key, details in APP_REGISTRY.items():
        if f"$ {app_key}" in command:
            logger.info(f"Launching app: {details['name']} via {details['open']}")
            os.system(details["open"])
            return f"Opening {details['name']}."
        elif f"& {app_key}" in command:
            logger.info(f"Closing app: {details['name']} via taskkill {details['process']}")
            return close_application_through_cmd(details["process"], f"Closed {details['name']}")

    for web_key, details in WEB_REGISTRY.items():
        if f"$ {web_key}" in command:
            logger.info(f"Opening URL: {details['url']} in browser")
            webbrowser.open_new_tab(details["url"])
            return f"Opening {details['name']}"

    if "$ taskmanager" in command or "$ task manager" in command or "$ resource monitor" in command:
        try:
            logger.info("Opening Task Manager via hotkey")
            keyboard.press_and_release("ctrl + shift + esc")
            return "Opening Task manager"
        except Exception as e:
            logger.error(f"Failed to open Task Manager: {e}", exc_info=True)
            return f"Failed to open Task manager: {e}"
    elif "& taskmanager" in command or "& task manager" in command or "& resource monitor" in command:
        logger.info("Close Task Manager requested (conflicted)")
        return "I am having conflits in closing Task manager, sir.\nStopping the task."
    
    elif "go to desktop" in command or "go to main screen" in command:
        try:
            logger.info("Going to desktop via hotkey")
            keyboard.press_and_release("win + d")
            return "You are on Desktop now."
        except Exception as e:
            logger.error(f"Failed to show desktop: {e}", exc_info=True)
            return f"Failed to go to desktop: {e}"

    elif "$ workplace" in command or "$ workspace" in command or "$ work place" in command or "$ work space" in command:
        logger.info("Opening full Workspace environment")
        webbrowser.open_new_tab("https://gemini.google.com/")
        os.system(f"antigravity-ide {os.getcwd()}")
        return "Opening Workspace."
    
    elif "& workplace" in command or "& workspace" in command or "& work place" in command or "& work space" in command:
        logger.info("Closing Workspace environment")
        return close_application_through_cmd("antigravity-ide.exe", "Closed Workspace")

    elif "$ advanced system settings" in command or "$ advance settings" in command or "$ system properties" in command:
        logger.info("Opening sysdm.cpl")
        os.system("start sysdm.cpl")
        return "Opening Advanced System Settings"

    elif "$ computer settings" in command:
        try:
            logger.info("Opening Windows settings")
            keyboard.press_and_release("win + i")
            return "Opening Settings"
        except Exception as e:
            logger.error(f"Failed to open computer settings: {e}", exc_info=True)
            return f"Failed to open settings: {e}"

    elif any(kw in command for kw in ("shutdown computer", "shut down computer", "shut down the computer", "shutdown system", "shutdown the system", "shutdown pc", "shut down pc", "turn off computer", "turn off the computer", "turn off pc", "power off computer", "power off pc")):
        logger.warning("System shutdown triggered!")
        os.system("shutdown /s /f /t 5")
        return "Shutting down the system now, sir."

    elif any(kw in command for kw in ("restart computer", "restart the computer", "restart system", "restart the system", "restart pc", "reboot computer", "reboot pc", "reboot the system", "reboot system")):
        logger.warning("System restart triggered!")
        os.system("shutdown /r /f /t 5")
        return "Restarting your machine now, sir."
    
    elif "clear memory" in command or "forget everything" in command or "clear your memory" in command:
        logger.info("Clearing memory history")
        clear_Memory()
        return "Cleared Memory at your command"

    elif "search memory" in command or "search your memory" in command or "recall" in command:
        parts = command.split("memory", 1) if "memory" in command else command.split("recall", 1)
        if len(parts) > 1 and parts[1].strip():
            query = parts[1].strip()
            logger.info(f"Searching memory for: '{query}'")
            results = LTM.search(query)
            if results:
                snippets = []
                for r in results[:5]:
                    prefix = "You said" if r['role'] == 'user' else "I replied"
                    content = r['content'][:80]
                    snippets.append(f"{prefix}: {content}")
                return "Here is what I found in my memory, sir:\n" + "\n".join(snippets)
            else:
                return "I'm afraid I found nothing matching that in my memory, sir."
        else:
            return "What would you like me to search for in my memory, sir?"

    elif "what do you remember" in command or "show memory" in command or "print memory" in command:
        logger.info("Printing memory statistics/details to terminal")
        output = LTM.print_memories(limit=10)
        print(output)
        return "I've displayed my recent memories on the terminal, sir."

    elif "memory stats" in command or "memory statistics" in command:
        logger.info("Getting memory database stats")
        s = LTM.stats()
        return (f"I have {s['total_memories']} memories across {s['total_sessions']} sessions. "
                f"Database size is {s['db_size_kb']} kilobytes.")

    elif "forget conversation" in command or "delete session" in command:
        sid = LTM.get_current_session_id()
        if sid:
            logger.info(f"Deleting conversation session ID: {sid}")
            count = LTM.delete_session(sid)
            return f"Done. I've forgotten {count} memories from this session."
        else:
            return "There is no active session to forget, sir."

    elif "system status" in command or "resource status" in command or "resource usage" in command:
        logger.info("System status stats requested")
        return format_stats_string()
        
    elif "cpu usage" in command:
        logger.info("System CPU usage requested")
        stats = get_system_stats()
        return f"Sir, CPU usage is currently at {stats['cpu_percent']} percent."
        
    elif "memory usage" in command or "ram usage" in command:
        logger.info("System RAM usage requested")
        stats = get_system_stats()
        return f"Sir, RAM usage is currently at {stats['ram_percent']} percent, with {stats['ram_used_gb']} gigabytes used out of {stats['ram_total_gb']} gigabytes."

    elif "search file" in command or "find file" in command or "serge file" in command:
        parts = command.split("file", 1)
        if len(parts) > 1:
            query = parts[1].strip()
            logger.info(f"Searching files matching: '{query}'")
            return search_files(query)
        else:
            return "Might I ask which file you’re looking for, sir?"
        
    else: 
        logger.debug(f"Command '{command}' not matched by system actions.")
        return None