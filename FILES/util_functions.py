import socket
import sys
import os
import speech_recognition as sr
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

# Ensure the root directory is in sys.path to import alfred_voice
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    from alfred_voice import AlfredVoiceModule
except ImportError as e:
    logger.error(f"Failed to import alfred_voice from project root: {e}")
    raise

# Initialize the pocket TTS voice module
ALFRED_VOICE = AlfredVoiceModule(voice_name="peter_yearsley")

@track_latency("util_functions.is_online")
def is_online(host="8.8.8.8", port=53, timeout=2) -> bool:
    """Checks if internet is connected."""
    try:
        socket.create_connection((host, port), timeout)
        return True
    except OSError:
        return False

@track_latency("util_functions.multi_replace")
def multi_replace(text: str, replacements: dict) -> str:
    """Replaces multiple strings based on a dictionary of {old: new}."""
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

@track_latency("util_functions.speak")
def speak(text: str = None) -> None:
    """Text to Speech function."""
    if not text:
        return

    if "sir" not in text.lower():
        text = f"{text.rstrip('.')}, sir."

    logger.info(f"Speaking: '{text}'")
    ALFRED_VOICE.speak(text)

@track_latency("util_functions.listen_command")
def listen_command() -> str:
    """Listens to the user speech using speech_recognition."""
    from FILES.gui_controller import set_input_mode
    r = sr.Recognizer()
    while True:
        with sr.Microphone() as source:
            print("Listening...")
            set_input_mode(False, "Listening...")
            audio = r.listen(source)

        try:
            print("Recognizing...")
            set_input_mode(False, "Recognizing...")
            query = r.recognize_google(audio, language="en-IN")
            if query:
                query_str = str(query).lower()
                logger.info(f"Speech recognition matched: '{query_str}'")
                set_input_mode(False, "")
                return query_str
        except sr.UnknownValueError:
            logger.debug("Speech recognition: Unknown value error (could not understand audio)")
            set_input_mode(False, "")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition Request Error: {e}")
            set_input_mode(False, "")
            return None

@track_latency("util_functions.search_files")
def search_files(filename: str, search_path="C:\\", is_commanded:bool=False, to_find:int=5) -> str:
    """Searches for files matching filename in search_path."""
    results = []
    query = filename.lower()
    logger.info(f"Searching files for query: '{query}' in directory: '{search_path}'")

    if not is_commanded: 
        speak("Allow me a moment, sir.")

    for root, dirs, files in os.walk(search_path):
        # Exclude common system junk paths to speed up search
        if "C:\\Windows\\WinSxS" in root or "AppData\\Local\\Temp" in root:
            continue
        
        for file in files:
            if query in file.lower():
                full_path = os.path.join(root, file)
                results.append(full_path)
                if len(results) >= to_find:
                    break
        if len(results) >= to_find:
            break

    if results:
        logger.info(f"Found {len(results)} file matches for: '{query}'")
        if is_commanded:
            return results[0]
        else:    
            speak("I found the following matches, sir:")
            for idx, path in enumerate(results, 1):
                print(f"{idx}. 📁 {path}")

            speak("Shall I open the first result for you?")
            confirmation = listen_command()
             
            if not confirmation or "cancel" in confirmation or "stop" in confirmation:
                logger.info("User cancelled opening the file.")
                return "Understood, I won’t open anything."

            if "yes" in confirmation or "open" in confirmation:
                try:
                    logger.info(f"Opening file: {results[0]}")
                    os.startfile(results[0])
                    return "Opening the file now."
                except Exception as e:
                    logger.error(f"Failed to start file: {e}")
                    return f"I'm afraid I couldn’t open it. The error was: {e}"

            return "Very well, I shall await further instructions."
    else:
        logger.info(f"No matching files found for query: '{query}'")
        return "I'm afraid I found no matching files, sir."

# Memory Container Import
try:
    from FILES.memory import MEMORY
except ImportError:
    from memory import MEMORY
