try:
    from FILES.util_functions import speak
except ImportError:
    from util_functions import speak     

from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

# Note: Playback is managed by the frontend/GUI through video stream URLs.
player = None
VOLUME_YOUTUBE = 100

@track_latency("youtube_player.play_youtube_audio")
def play_youtube_audio(query: str) -> str:
    """Fetches video URL from YouTube using yt_dlp and sends it to the GUI."""
    speak("Let me fetch that, sir.")

    import yt_dlp
    from FILES.gui_controller import show_data
    
    logger.info(f"Searching YouTube for: '{query}'")
    try:
        ydl_opts = {
            'format': 'best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch1'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                video_url = info['entries'][0]['url']
                logger.info(f"Found YouTube video URL: {video_url}")
                show_data([f"video:{video_url}"])
                return "[KEEP_UI] Playing from YouTube."
            else:
                logger.warning(f"No YouTube entries found for query: '{query}'")
                return "I'm sorry, I couldn't find a video for that."
    except Exception as e:
        logger.error(f"YouTube yt_dlp search error: {e}", exc_info=True)
        return "I'm sorry, finding the video failed due to YouTube restrictions or an error."

@track_latency("youtube_player.stop_youtube_audio")
def stop_youtube_audio() -> str:
    """Stops YouTube playback by clearing GUI data."""
    logger.info("Stopping YouTube playback")
    from FILES.gui_controller import show_data
    show_data([])
    return "Stopped YouTube playback, sir."
        
@track_latency("youtube_player.set_volume_youtube")
def set_volume_youtube() -> None:
    """Stub to keep backward compatibility with volume requests."""
    global VOLUME_YOUTUBE
    logger.info(f"YouTube volume setting updated to {VOLUME_YOUTUBE}")
