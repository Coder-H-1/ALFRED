"""
`utils.py` loads the Large Language Model (LLM)

Functions:
    get_time() -> str
    get_date() -> str
    get_greeting() -> str
    clear_Memory() -> None
    butler_response(query: str) -> str

    Note : 'query' is the input given by the user (either through voice input or from text input)

Working:
    It creates an object called `MEMORY` -> Controls and recalls chat history

    It creates another object called `LLM` -> load LLaMa model 
                :-> n_ctx       = 6144   (tokens input)
                :-> max_token   = 100         (token output per prompt)

    
"""


import os
import datetime

try: from FILES.memory import Memory
except ModuleNotFoundError: 
    from memory import Memory

from llama_cpp import Llama


MEMORY = Memory()


def get_time() -> str:
    now = datetime.datetime.now()
    return now.strftime("It is %I:%M %p, sir.")  # 12-hour format


def get_date() -> str:
    today = datetime.datetime.now()
    return today.strftime("Today is %A, %d %B %Y.")


def get_greeting() -> str:
    hour = datetime.datetime.now().hour

    _time = get_time().replace("It is ", "The time is ").replace(", sir." , "")
    _date = get_date().replace("." , " ")
    Time_and_Date = f"{_date} and {_time}"
    if 5 <= hour < 12:
        greet = f"Good morning, sir."
    elif 12 <= hour < 17:
        greet = f"Good afternoon, sir."
    elif 17 <= hour < 21:
        greet = f"Good evening, sir."
    else:
        greet = "Working late are we sir."
    
    MEMORY.add_to_history(Time_and_Date, greet)
    return greet
    

def clear_Memory() -> None: MEMORY.clean_history()


# FOR LLM

def get_optimal_threads(reserve=2) -> int:
    total = os.cpu_count()
    threads = max(1, total - reserve)
    print(f":> Using {threads} threads out of {total} logical cores.")
    return int(threads)


MODEL_PATH = "FILES/model/L3.1-Dark-Planet-SpinFire-Uncensored-8B-D_AU-Q4_k_m.gguf"

LLM = Llama( model_path=MODEL_PATH, n_ctx=3072, n_threads=get_optimal_threads(), verbose=False )

def Answer_length(text:str) -> int:
    if "in brief" in text or "in detail" in text or "have a lot of time" in text:
        text = text.replace("in detail", "").replace("have a lot of time" , "").replace("in brief" , "")
        return 250, text
    
    elif "in short" in text or "just short" in text or "i am in a hurry" in text:
        text = text.replace("in short", "").replace("just short" , "").replace("i am in a hurry" , "")
        return 75, text
    
    else:
        return 150, text



def Responder(prompt: str) -> str:

    MEMORY.remember("last_command", prompt)

    history : str = MEMORY.get_history()   ## Chat History
     
    inject = (
        "Full Name : Automated Limited Functionality Responsive Educational Development (system). or ALFRED.\n"
        "Work : Replay user with polite, relevant and brief answers.\n"
        "Functionality : ALFRED is programmed with multiple assistance system included text generation, open-closing applications and many more.\n "
        f"{history}\n"
        f"User said: {prompt}\nALFRED: "
    )

    Answer_LENGTH, prompt =  Answer_length(prompt)

    out = LLM(inject , max_tokens = Answer_LENGTH, stop=["User:", "Butler:"], echo=False)
    answer : str = out["choices"][0]["text"].strip()
    
    if "User said" in answer:
        try: answer :str = answer.split("User said")[0]
        except: pass

    answer : str = answer.replace("Assistant:" , "").replace("ALFRED:" , "")
    MEMORY.add_to_history(prompt, answer)
    return answer

if __name__ == "__main__":

    while True:
        text = str(input(">> ")).strip()
        print(Responder(text)) 

