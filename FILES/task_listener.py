
import speech_recognition as sr
import pyaudio
import json
from vosk import Model, KaldiRecognizer
from DATA_worker import get_Data_state


# listen_commands configuration
RECOGNIZER = sr.Recognizer()
MIC = sr.Microphone()


vosk_model = Model("FILES\\model")
recognizer = KaldiRecognizer(vosk_model, 16000)

def listen_command_offline() -> str:
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
    

    stream.start_stream()

    print(":> Listening (Vosk)...")

    while True:
        recognizer.AcceptWaveform(b'')  # flush
        data = stream.read(4000, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result = recognizer.Result()
            text = json.loads(result).get("text", "")
            if text:
                print(f"🗣️ You said: {text}")
                return text.lower()




def listen_command_online() -> str:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print(":> Listening (online)...")
        audio = r.listen(source)
    
    try:
        print("Recognizing...")
        query = r.recognize_google(audio, language="en-IN")
        print(f"User : {query}")
    except Exception as Err:
        query = "none"
    
    return str(query)


def listen_command() -> str:
    if get_Data_state:
        return listen_command_online()
    else:
        return listen_command_offline()

