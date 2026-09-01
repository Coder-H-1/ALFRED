"""
command_components package for modular command execution in ALFRED.
"""
from FILES.command_components.search import handle_search_query
from FILES.command_components.window_management import (
    handle_move_window,
    handle_pin_window,
    handle_unpin_window,
    handle_clean_gui,
    BOX_MAPPING,
    ZONE_MAPPING
)
from FILES.command_components.media_controls import (
    handle_video_controls,
    handle_youtube_play,
    handle_youtube_stop,
    handle_youtube_volume,
    handle_master_volume,
    handle_brightness
)
from FILES.command_components.system_status import (
    handle_time,
    handle_date,
    handle_system_status,
    handle_cpu_usage,
    handle_memory_usage
)
from FILES.command_components.app_launcher import (
    close_application_through_cmd,
    handle_app_registry,
    handle_web_registry,
    handle_task_manager,
    handle_desktop,
    handle_workspace,
    handle_system_settings,
    handle_power_control,
    handle_file_search,
    APP_REGISTRY,
    WEB_REGISTRY
)
from FILES.command_components.memory_commands import (
    handle_repeat_answer,
    handle_clear_memory,
    handle_search_memory,
    handle_show_memory,
    handle_memory_stats,
    handle_forget_conversation
)
from FILES.command_components.weather_commands import handle_weather
from FILES.command_components.log_commands import handle_decompress_logs, handle_compress_logs
