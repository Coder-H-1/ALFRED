import os
import webbrowser
import keyboard
from FILES.util_functions import search_files
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

# Core registries for commands
APP_REGISTRY = {
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
    "stackoverflow":   {"url": "https://www.stackoverflow.com", "name": "stackoverflow"},
    "google":           {"url": "https://www.google.com", "name": "Google"},
    "search":           {"url": "https://www.google.com", "name": "Google"},
    "chatgpt":          {"url": "https://www.chatgpt.com", "name": "ChatGPT"},
    "gemini":          {"url": "https://gemini.google.com/app", "name": "Gemini"},
}

from FmWk.tools.system_tools import (
    open_app as mcp_open_app,
    close_app as mcp_close_app,
    open_workspace as mcp_open_workspace,
    close_workspace as mcp_close_workspace,
    show_desktop as mcp_show_desktop,
)

@track_latency("commands.close_application_through_cmd")
def close_application_through_cmd(process_name: str, return_response: str = None) -> str:
    logger.info(f"Closing application via unified MCP: {process_name}")
    res = mcp_close_app(process_name)
    return return_response or res.get("status") or res.get("error")

@track_latency("commands.process_command.app_launcher")
def handle_app_registry(command: str) -> str:
    for app_key in APP_REGISTRY.keys():
        if f"$ {app_key}" in command:
            logger.info(f"Launching app '{app_key}' via unified MCP")
            res = mcp_open_app(app_key)
            return res.get("status") or res.get("error")
        elif f"& {app_key}" in command:
            logger.info(f"Closing app '{app_key}' via unified MCP")
            res = mcp_close_app(app_key)
            return res.get("status") or res.get("error")
    return None

@track_latency("commands.process_command.web_launcher")
def handle_web_registry(command: str) -> str:
    for web_key in WEB_REGISTRY.keys():
        clean_key = "".join(web_key.split(" "))
        if f"${clean_key}" in "".join(command.split(" ")):
            logger.info(f"Opening web app '{web_key}' via unified MCP")
            res = mcp_open_app(web_key)
            return res.get("status") or res.get("error")
    return None

@track_latency("commands.process_command.task_manager")
def handle_task_manager(command: str) -> str:
    if "$ taskmanager" in command or "$ task manager" in command or "$ resource monitor" in command:
        app_target = "task manager" if "task" in command else "resource monitor"
        logger.info(f"Opening Task Manager / Resource Monitor via unified MCP: {app_target}")
        res = mcp_open_app(app_target)
        return res.get("status") or res.get("error")
    elif "& taskmanager" in command or "& task manager" in command or "& resource monitor" in command:
        app_target = "task manager" if "task" in command else "resource monitor"
        logger.info(f"Closing Task Manager / Resource Monitor via unified MCP: {app_target}")
        res = mcp_close_app(app_target)
        return res.get("status") or res.get("error")
    return None

@track_latency("commands.process_command.desktop")
def handle_desktop(command: str) -> str:
    logger.info("Triggering show desktop via unified MCP")
    res = mcp_show_desktop()
    return res.get("status") or res.get("error")

@track_latency("commands.process_command.workspace")
def handle_workspace(command: str) -> str:
    if "$ workplace" in command or "$ workspace" in command or "$ work place" in command or "$ work space" in command:
        logger.info("Opening full Workspace environment via unified MCP")
        res = mcp_open_workspace()
        return res.get("status") or res.get("error")
    elif "& workplace" in command or "& workspace" in command or "& work place" in command or "& work space" in command:
        logger.info("Closing Workspace environment via unified MCP")
        res = mcp_close_workspace()
        return res.get("status") or res.get("error")
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
