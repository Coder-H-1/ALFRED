import os
import webbrowser
import keyboard
from FILES.util_functions import search_files
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

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
def close_application_through_cmd(process_name: str, return_response: str = None) -> str:
    logger.info(f"Attempting to close process: {process_name}")
    if " " in process_name:
        process_name = process_name.split(" ")[-1]
    os.system(f"taskkill /f /im {process_name}")
    return return_response or f"Closed {process_name}"

@track_latency("commands.process_command.app_launcher")
def handle_app_registry(command: str) -> str:
    for app_key, details in APP_REGISTRY.items():
        if f"$ {app_key}" in command:
            logger.info(f"Launching app: {details['name']} via {details['open']}")
            os.system(details["open"])
            return f"Opening {details['name']}."
        elif f"& {app_key}" in command:
            logger.info(f"Closing app: {details['name']} via taskkill {details['process']}")
            return close_application_through_cmd(details["process"], f"Closed {details['name']}")
    return None

@track_latency("commands.process_command.web_launcher")
def handle_web_registry(command: str) -> str:
    for web_key, details in WEB_REGISTRY.items():
        if f"$ {web_key}" in command:
            logger.info(f"Opening URL: {details['url']} in browser")
            webbrowser.open_new_tab(details["url"])
            return f"Opening {details['name']}"
    return None

@track_latency("commands.process_command.task_manager")
def handle_task_manager(command: str) -> str:
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
    return None

@track_latency("commands.process_command.desktop")
def handle_desktop(command: str) -> str:
    try:
        logger.info("Going to desktop via hotkey")
        keyboard.press_and_release("win + d")
        return "You are on Desktop now."
    except Exception as e:
        logger.error(f"Failed to show desktop: {e}", exc_info=True)
        return f"Failed to go to desktop: {e}"

@track_latency("commands.process_command.workspace")
def handle_workspace(command: str) -> str:
    if "$ workplace" in command or "$ workspace" in command or "$ work place" in command or "$ work space" in command:
        logger.info("Opening full Workspace environment")
        webbrowser.open_new_tab("https://gemini.google.com/")
        os.system(f"antigravity-ide {os.getcwd()}")
        return "Opening Workspace."
    elif "& workplace" in command or "& workspace" in command or "& work place" in command or "& work space" in command:
        logger.info("Closing Workspace environment")
        return close_application_through_cmd("antigravity-ide.exe", "Closed Workspace")
    return None

@track_latency("commands.process_command.system_settings")
def handle_system_settings(command: str) -> str:
    if "$ advanced system settings" in command or "$ advance settings" in command or "$ system properties" in command:
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
    return None

@track_latency("commands.process_command.power_control")
def handle_power_control(command: str) -> str:
    if any(kw in command for kw in ("shutdown computer", "shut down computer", "shut down the computer", "shutdown system", "shutdown the system", "shutdown pc", "shut down pc", "turn off computer", "turn off the computer", "turn off pc", "power off computer", "power off pc")):
        logger.warning("System shutdown triggered!")
        os.system("shutdown /s /f /t 5")
        return "Shutting down the system now, sir."
    elif any(kw in command for kw in ("restart computer", "restart the computer", "restart system", "restart the system", "restart pc", "reboot computer", "reboot pc", "reboot the system", "reboot system")):
        logger.warning("System restart triggered!")
        os.system("shutdown /r /f /t 5")
        return "Restarting your machine now, sir."
    return None

@track_latency("commands.process_command.file_search")
def handle_file_search(command: str) -> str:
    parts = command.split("file", 1)
    if len(parts) > 1:
        query = parts[1].strip()
        logger.info(f"Searching files matching: '{query}'")
        return search_files(query)
    else:
        return "Might I ask which file you’re looking for, sir?"
