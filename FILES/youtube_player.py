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
    """Fetches video URL from YouTube using yt_dlp with automatic fallback for embed-disabled videos."""
    speak("Let me fetch that, sir.")

    import yt_dlp
    from FILES.gui_controller import show_data
    
    logger.info(f"Searching YouTube for: '{query}'")
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'noplaylist': True,
            'quiet': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'default_search': 'ytsearch5'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            entries = [e for e in info.get('entries', []) if e]
            if not entries:
                logger.warning(f"No YouTube entries found for query: '{query}'")
                return "I'm sorry, I couldn't find a video for that."

            embeddable_entry = None
            first_entry_direct_url = None

            for idx, entry in enumerate(entries):
                v_id = entry.get('id')
                can_embed = entry.get('playable_in_embed') is not False
                if can_embed and v_id:
                    embeddable_entry = entry
                    break
                elif idx == 0 and entry.get('url'):
                    first_entry_direct_url = entry.get('url')

            if embeddable_entry:
                v_id = embeddable_entry.get('id')
                logger.info(f"Selected embeddable YouTube video ID: {v_id} ('{embeddable_entry.get('title')}')")
                show_data([f"youtube:{v_id}"])
                return "[KEEP_UI] Playing from YouTube."
            elif first_entry_direct_url:
                logger.info("No embeddable entry found; falling back to direct video stream.")
                show_data([f"video:{first_entry_direct_url}"])
                return "[KEEP_UI] Playing video via direct stream."
            elif entries[0].get('id'):
                show_data([f"youtube:{entries[0]['id']}"])
                return "[KEEP_UI] Playing from YouTube."
            else:
                return "I'm sorry, I couldn't find a playable stream for that video."
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
