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
    set_volume_youtube
)
import FILES.youtube_player as youtube_player
from FILES.gui_controller import set_video_control
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

@track_latency("commands.process_command.video_controls")
def handle_video_controls(command: str) -> str:
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

@track_latency("commands.process_command.youtube_play")
def handle_youtube_play(command: str) -> str:
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

@track_latency("commands.process_command.youtube_stop")
def handle_youtube_stop(command: str) -> str:
    logger.info("Stopping YouTube music")
    return stop_youtube_audio()

@track_latency("commands.process_command.youtube_volume")
def handle_youtube_volume(command: str) -> str:
    if "set" in command:
        for word in command.split():
            if word.isdigit():
                youtube_player.VOLUME_YOUTUBE = int(word)
                logger.info(f"Setting YouTube volume to {youtube_player.VOLUME_YOUTUBE}")
                set_volume_youtube()
                return f"Youtube's volume is now set to : {youtube_player.VOLUME_YOUTUBE}"
        return "Couldn't set volume could you please repeat the command, sir."

    if "increase" in command:
        youtube_player.VOLUME_YOUTUBE += 10
        logger.info(f"Increasing YouTube volume to {youtube_player.VOLUME_YOUTUBE}")
        set_volume_youtube()
        return f"Youtube volume is now set to : {youtube_player.VOLUME_YOUTUBE} %"
    elif "decrease" in command:
        youtube_player.VOLUME_YOUTUBE -= 10
        logger.info(f"Decreasing YouTube volume to {youtube_player.VOLUME_YOUTUBE}")
        set_volume_youtube()
        return f"Youtube volume is now set to : {youtube_player.VOLUME_YOUTUBE} %"
    return "Could not adjust YouTube volume, sir."

@track_latency("commands.process_command.volume")
def handle_master_volume(command: str) -> str:
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
    return "Could not adjust volume, sir."

@track_latency("commands.process_command.brightness")
def handle_brightness(command: str) -> str:
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
    return "Could not adjust brightness, sir."
