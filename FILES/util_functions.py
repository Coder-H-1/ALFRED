########################################################################################################################################
### > Internet ###
import requests

def get_Data_state() -> bool:
    "Checks if internet is connected or not -> returns True/False"

    try:
        requests.get(f"https://www.google.com")
        return True
    except:
        return False

########################################################################################################################################
### > Text editing ###

class EDIT:
    "Used to edit a list of strings in a sentence without using str.replace() function"

    def __init__(self, text:str, FROM_str:list, TO_str:list=None) -> None:
        self.original_text  : str  = str(text).lower()
        self.FROM_str       : list = list(FROM_str)
        self.TO_str         : list = list(TO_str)
    
    def replace_to_none(self) -> str:
        "Replaces all the items in list( FROM_str ) to \"\""

        text = self.original_text
        for i in range( int(len(self.FROM_str)) ):
            text = text.replace( str(self.FROM_str[i]).lower() , "")

        return text
    
    def replace(self) -> str:
        "Replaces items list( FROM_STR ) to items in list( TO_str )"

        text = self.original_text
        for i in range( int(len(self.FROM_str)) ):
            try:
                text = text.replace( str(self.FROM_str[i]).lower() , str(self.TO_str[i]))
            except: 
                text = text.replace( str(self.FROM_str[i]).lower() , str(self.TO_str[0]))
            

        return text

#########################################################################################################################################
### Speech ###

import threading
import pyttsx3

_speak_lock = threading.Lock()
SPEAK_ENGINE = pyttsx3.init("sapi5")
SPEAK_VOICES = SPEAK_ENGINE.getProperty("voices")
SPEECH_RATE = 170   


def speak(text: str = None, speech_rate:int=SPEECH_RATE) -> None:
    "Text to Speech function"

    voice_index = (3 if len(SPEAK_VOICES) >= 3 else 0)  # I have male British English Language pack at number 3; 0 > Microsoft default male voice  
    SPEAK_ENGINE.setProperty("voice", SPEAK_VOICES[voice_index].id) 
    SPEAK_ENGINE.setProperty("rate" , speech_rate)

            
    if "sir" not in text.lower():
        text = f"{text.rstrip('.')}, sir."

    print(f"Alfred: {text}")

    with _speak_lock:  # Lock to avoid runtime crash
        SPEAK_ENGINE.say(text)  
        SPEAK_ENGINE.runAndWait()

######################################################################################################################
### > Speech Recognition

import speech_recognition as sr

# listen_commands configuration
RECOGNIZER = sr.Recognizer()
MIC = sr.Microphone()
    

def listen_command() -> str:
    r = sr.Recognizer()
    while True:
        with sr.Microphone() as source:
            print(":> Listening (online)...")
            audio = r.listen(source)

        try:
            print("Recognizing...")
            query = r.recognize_google(audio, language="en-IN")
            if query:
                print(f"User said : {query}")
                return str(query).lower()
        except:
            return None

######################################################################################################################

