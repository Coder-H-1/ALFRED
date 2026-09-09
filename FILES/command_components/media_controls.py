from FILES.gui_controller import set_video_control
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

@track_latency("commands.process_command.video_controls")
def handle_video_controls(command: str) -> str:
    """Controls the Next.js GUI embedded video player overlay."""
    if "video audio only" in command or "play audio only" in command:
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
    return None
