"""
`utils.py` loads the Large Language Model (LLM)

Functions:
    get_time() -> str
    get_date() -> str
    get_greeting() -> str
    clear_Memory() -> None
    Response(query: str) -> str

    Note : 'query' is the input given by the user (either through voice input or from text input)

Working:
    It creates an object called `MEMORY` -> Controls and recalls chat history

    It creates another object called `LLM` -> load LLaMa model 
                :-> n_ctx       = 2048        (tokens input)
                :-> max_token   = 100         (token output per prompt)

    
"""

import os
import datetime
import random

from llama_cpp      import Llama

try: 
    from FILES.memory           import Memory, MEMORY    # Do not remove Memory from here ; many functions uses it 
    from FILES.util_functions   import EDIT as Text_Editor
except ModuleNotFoundError: 
    from memory                 import Memory, MEMORY     ## for util file debugging
    from util_functions         import EDIT as Text_Editor



def get_time() -> str: ## Checks Time > returns a string ("It is %I:%M %p, sir")
    now = datetime.datetime.now()
    return now.strftime("It is %I:%M %p, sir.")  # 12-hour format

def get_date() -> str:  ## Checks Date > returns a string ("Today is %A, %d %B %Y.") 
    today = datetime.datetime.now()
    return today.strftime("Today is %A, %d %B %Y.")

def get_greeting() -> str: ## Greets user
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
    
def clear_Memory() -> None: MEMORY.clean_history()  # Clears all the previous Session chat history

# FOR LLM

def get_optimal_threads(reserve=2) -> int: ## For CPU usage control  > reserves atleast 2 cpu cores for Operating System 
    total:int = os.cpu_count()
    threads:int = max(1, total - reserve)
    print(f":> Using {threads} threads out of {total} logical cores.")
    return int(threads)

MODEL_PATH:str = "FILES/model/*Model_name.gguf"  ### Change Model_Name if you want to use 1  
  
LLM: object = Llama(        ### loads LLM model using LLama class
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_threads=get_optimal_threads(),
    verbose=False 
    )

def Responder(prompt: str) -> str: ### Reponds user query
    "Reponds user query using Chat Model"

    MEMORY.remember("last_command", prompt) 
    ### sets key = "last_command" to value = (prompt)

    history: str = MEMORY.get_history()   ## Chat History
     
    inject: str = (  ### Prompt 
        "Full Name : Automated Limited Functionality Responsive Educational Development (system). or ALFRED.\n"
        "Work : Replay user with polite, relevant and brief answers.\n"
        "Functionality : ALFRED is programmed with multiple assistance system included text generation, open-closing applications and many more.\n "
        f"{history}\n"
        f"User said: {prompt}\nALFRED: "
    )

    out: object = LLM(inject , max_tokens = 150, stop=["User:", "ALFRED:"], echo=False)  
    ### Prompts the LLM model and expects a reply    
    ### max_tokens = length of responce ; here 150 = words/tokens

    answer: str = out["choices"][random.randint(0,1)]["text"].strip()  
    ### Chooses an answer from LLM model 
    
    if "User said" in answer:
        try: 
            answer: str = answer.split("User said")[0] ### returns answer from ['answer', 'unwanted']
        except: pass

    answer: str = Text_Editor(
        text=answer, FROM_str=["Assistant:", "ALFRED:"]
        ).replace_to_none()  ### Replaces string names to ""
    
    MEMORY.add_to_history(prompt, answer)
    return answer

# if __name__ == "__main__":   # to debug changes made in file

#     while True:
#         text:str = str(input(">> ")).strip()
#         print(Responder(text)) 

