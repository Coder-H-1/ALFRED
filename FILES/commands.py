"""
commands.py — Master command dispatcher for ALFRED.

Refactored to be modular and scalable, delegating specific domain tasks
to specialized modules in FILES/command_components/.
"""
from FILES.util_functions import multi_replace
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

# Component handlers & registries
from FILES.command_components import (
    handle_search_query,
    handle_move_window,
    handle_pin_window,
    handle_unpin_window,
    handle_clean_gui,
    handle_video_controls,
    handle_youtube_play,
    handle_youtube_stop,
    handle_youtube_volume,
    handle_master_volume,
    handle_brightness,
    handle_time,
    handle_date,
    handle_system_status,
    handle_cpu_usage,
    handle_memory_usage,
    close_application_through_cmd,
    handle_app_registry,
    handle_web_registry,
    handle_task_manager,
    handle_desktop,
    handle_workspace,
    handle_system_settings,
    handle_power_control,
    handle_file_search,
    handle_repeat_answer,
    handle_clear_memory,
    handle_search_memory,
    handle_show_memory,
    handle_memory_stats,
    handle_forget_conversation,
    handle_weather,
    handle_decompress_logs,
    handle_compress_logs,
    BOX_MAPPING,
    ZONE_MAPPING,
    APP_REGISTRY,
    WEB_REGISTRY
)

logger = get_logger(__name__)

@track_latency("commands.process_command")
def process_command(command: str) -> str:
    """Dispatches a text/voice command to the appropriate component handler."""
    logger.info(f"Processing command: '{command}'")
    
    command = multi_replace(str(command), {"open": "$", "start": "$", "close": "&", "end": "&"})
    
    # 1. Wikipedia / Online Search Integration
    if command.startswith("who is ") or command.startswith("what is ") or command.startswith("tell me about "):
        return handle_search_query(command)

    # 2. Window & GUI Zone Controls
    if "move window" in command or "move box" in command:
        return handle_move_window(command)

    elif "pin window" in command or "pin box" in command:
        return handle_pin_window(command)

    elif "unpin window" in command or "unpin box" in command:
        return handle_unpin_window(command)
        
    elif "clean the gui" in command or "clear the screen" in command:
        return handle_clean_gui(command)

    # 3. Log Management
    elif "decompress logs" in command or "expand logs" in command:
        return handle_decompress_logs(command)

    elif "compress logs" in command:
        return handle_compress_logs(command)

    # 4. Weather
    elif "check weather outside" in command:
        return handle_weather(command)
            
    # 5. Memory & Recall
    elif "could you repeat what you just said" in command or "repeat what you just said" in command or "repeat the answer" in command:
        return handle_repeat_answer(command)

    # 6. Video Controls
    elif any(kw in command for kw in ("video audio only", "play audio only", "show video", "enable video", "mute video", "unmute video", "rewind video", "go back", "forward video", "skip ahead")):
        res = handle_video_controls(command)
        if res:
            return res
       
    # 7. YouTube Playback & Volume
    if "play from youtube" in command or "play on youtube" in command or "on youtube" in command:
        return handle_youtube_play(command)

    elif "stop youtube" in command or "stop music" in command:
        return handle_youtube_stop(command)

    elif "youtube volume" in command:
        return handle_youtube_volume(command)

    # 8. Master Volume
    elif "volume" in command:
        return handle_master_volume(command)

    # 9. Brightness
    elif "brightness" in command:
        return handle_brightness(command)

    # 10. Time & Date
    elif "time" in command and "what" in command:
        return handle_time()

    elif "date" in command or "day" in command: 
        if "what" in command:
            return handle_date()

    # 11. Dynamic Apps & Web Launcher
    app_res = handle_app_registry(command)
    if app_res:
        return app_res

    web_res = handle_web_registry(command)
    if web_res:
        return web_res

    # 12. Task Manager & Desktop
    tm_res = handle_task_manager(command)
    if tm_res:
        return tm_res
    
    elif "go to desktop" in command or "go to main screen" in command:
        return handle_desktop(command)

    # 13. Workspace Environment
    ws_res = handle_workspace(command)
    if ws_res:
        return ws_res

    # 14. System Settings
    sys_res = handle_system_settings(command)
    if sys_res:
        return sys_res

    # 15. Power Controls (Shutdown / Restart)
    power_res = handle_power_control(command)
    if power_res:
        return power_res
    
    # 16. Memory Management Details
    elif "clear memory" in command or "forget everything" in command or "clear your memory" in command:
        return handle_clear_memory(command)

    elif "search memory" in command or "search your memory" in command or "recall" in command:
        return handle_search_memory(command)

    elif "what do you remember" in command or "show memory" in command or "print memory" in command:
        return handle_show_memory(command)

    elif "memory stats" in command or "memory statistics" in command:
        return handle_memory_stats(command)

    elif "forget conversation" in command or "delete session" in command:
        return handle_forget_conversation(command)

    # 17. System Hardware Status
    elif "system status" in command or "resource status" in command or "resource usage" in command:
        return handle_system_status()
        
    elif "cpu usage" in command:
        return handle_cpu_usage()
        
    elif "memory usage" in command or "ram usage" in command:
        return handle_memory_usage()

    # 18. File Search
    elif "search file" in command or "find file" in command or "serge file" in command:
        return handle_file_search(command)
        
    else: 
        logger.debug(f"Command '{command}' not matched by system actions.")
        return None