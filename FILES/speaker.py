"""
Speech function for Windows
"""


import threading
import pyttsx3

_speak_lock = threading.Lock()
SPEAK_ENGINE = pyttsx3.init("sapi5")
SPEAK_VOICES = SPEAK_ENGINE.getProperty("voices")
SPEECH_RATE = 170   



def speak(text: str = None, speech_rate:int=SPEECH_RATE) -> None:
    voice_index = 3 if len(SPEAK_VOICES) >= 3 else 0  ### If you have multiple language installed set it to (0) for English
    SPEAK_ENGINE.setProperty("voice", SPEAK_VOICES[voice_index].id)
    SPEAK_ENGINE.setProperty("rate" , speech_rate)

    if text:
        if "sir" not in text.lower():
            text = f"{text.rstrip('.')}, sir."
        print(f"Alfred: {text}")
        with _speak_lock:  # 🚨 Lock to avoid runtime crash
            SPEAK_ENGINE.say(text)
            SPEAK_ENGINE.runAndWait()

