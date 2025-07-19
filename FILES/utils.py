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
                :-> n_ctx       = 6144  (6 * 1024)   (tokens input)
                :-> max_token   = 100                (token output per prompt)

                NOTE:
                lower the `n_ctx`, the lower the ram usage and less relevation of the answer to previous prompt.
                
                too much high `n_ctx`, the higher the ram usage and more accurate and relevant the answer.
    
"""


import os
import datetime


from FILES.memory import Memory
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
    threads = max(1, total - reserve) ## reserves 2 for Operating System
    print(f":> Using {threads} threads out of {total} logical cores.")
    return int(threads)


MODEL_PATH = "model/openhermes-2.5-mistral-7b.Q4_K_M.gguf"

LLM = Llama( model_path=MODEL_PATH, n_ctx=6144, n_threads=get_optimal_threads(), verbose=False )

def butler_response(prompt: str) -> str:
    _time = get_time().replace("It is ", "The time is ").replace(", sir." , "")
    _date = get_date().replace("." , " and")
    Time_and_Date = f"{_date} and {_time}"

    MEMORY.remember("last_command", prompt)

    title = MEMORY.recall("user_name") or "sir"
    
    history = MEMORY.get_history()

    inject = (
        "You are Alfred, a polite british assistant."
        f"Always refers the user as {title}"
        "Always respond respectfully, and keep your replies relevant and short."
        f"{Time_and_Date}\n"
        f"{history}\n"
        f"User said: {prompt}\nButler:"
    )

    out = LLM(inject, max_tokens=100, stop=["User:", "Butler:"], echo=False)
    answer = out["choices"][0]["text"].strip()
    MEMORY.add_to_history(prompt, answer)

    if "User said" in answer:
        try:
            answer, _ = answer.split("User said")
        except:
            pass

    answer = answer.replace("Assistant:" , "")
    return answer



