# youtube_player.py

import vlc
import yt_dlp
from FILES.util_functions import speak
player = None
VOLUME_YOUTUBE = 100

def play_youtube_audio(url_or_query):
    global player

    speak("Let me fetch that, sir.")

    # Handle direct URL or search query
    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch",
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_or_query, download=False)
            if "entries" in info:
                info = info["entries"][0]

            audio_url = info["url"]
            title = info.get("title", "the audio")

            player = vlc.MediaPlayer(audio_url)
            player.play()

            return (f"Now playing: {title}")
    except Exception as e:
        print(f"[YouTube ERROR]: {e}")
        return ("I'm sorry, I couldn't play it from YouTube.")

def stop_youtube_audio():
    global player
    if player:
        player.stop()
        return ("Stopped YouTube playback, sir.")
    else:
        return "Player not working, sir."
        

def set_volume_youtube():
    global player, VOLUME_youtube
    if player:
        player.audio_set_volume(VOLUME_youtube)
        
        
