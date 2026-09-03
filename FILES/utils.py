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
import re
from llama_cpp import Llama
from FILES.util_functions import multi_replace, MEMORY
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency


logger = get_logger(__name__)

@track_latency("utils.get_time")
def get_time() -> str:
    now = datetime.datetime.now()
    return now.strftime("It is %I:%M %p, sir.")  # 12-hour format

@track_latency("utils.get_date")
def get_date() -> str:
    today = datetime.datetime.now()
    return today.strftime("Today is %A, %d %B %Y.")

@track_latency("utils.get_greeting")
def get_greeting() -> str:
    hour = datetime.datetime.now().hour
    _time = get_time().replace("It is ", "The time is ").replace(", sir." , "")
    _date = get_date().replace("." , " ")
    Time_and_Date = f"{_date} and {_time}"
    
    if 5 <= hour < 12:
        greet = "Good morning, sir."
    elif 12 <= hour < 17:
        greet = "Good afternoon, sir."
    elif 17 <= hour < 21:
        greet = "Good evening, sir."
    else:
        greet = "Working late are we sir."
    
    logger.info(f"Generated greeting: '{greet}' for context: {Time_and_Date}")
    MEMORY.add_to_history(Time_and_Date, greet)
    return greet
    
@track_latency("utils.clear_Memory")
def clear_Memory() -> None:
    logger.info("Cleaning conversation history memory.")
    MEMORY.clean_history()

def get_optimal_threads(reserve=2) -> int:
    total = os.cpu_count() or 4
    threads = max(1, total - reserve)
    logger.info(f"Using {threads} threads out of {total} logical cores (reserved {reserve} cores).")
    return int(threads)

# Construct absolute/relative path safely
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(_BASE_DIR, "FILES", "model", "model.gguf")

logger.info(f"Initializing LLaMA model from path: {MODEL_PATH}")

LLM = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,
    n_threads=get_optimal_threads(),
    verbose=False 
)

@track_latency("utils.Responder")
def Responder(prompt: str) -> str:
    logger.info(f"LLM Responder received prompt: '{prompt}'")
    MEMORY.remember("last_command", prompt) 

    history = MEMORY.get_history()
     
    inject = (
        "ALFRED is a polite AI assistant.\n"
        f"{history}\n"
        f"User said: {prompt}\nALFRED: "
    )

    logger.debug(f"Prompt injection content length: {len(inject)}")
    stop_tokens = ["User:", "ALFRED:", "note:", "Note:", "NOTE:", "\nnote:", "\nNote:", "\nNOTE:", "\nUser said:", "Alfred:"]
    out = LLM(inject, max_tokens=500, stop=stop_tokens, echo=False)  

    answer = out["choices"][0]["text"]
    finish_reason = out["choices"][0].get("finish_reason", "")
    
    # Dynamic Elastic Output Modal
    if finish_reason == "length":
        logger.debug("Response reached max_tokens limit; applying elastic extension.")
        stripped_ans = answer.strip()
        if stripped_ans and stripped_ans[-1] not in ['.', '!', '?', '"', '\'']:
            elastic_inject = inject + answer
            elastic_out = LLM(elastic_inject, max_tokens=75, stop=stop_tokens, echo=False)
            answer += elastic_out["choices"][0]["text"]

    answer = answer.strip()
    
    # Crop output text before any "NOTE:", "Note:", or "note:"
    note_match = re.search(r'(?i)\bnote\s*:', answer)
    if note_match:
        logger.info(f"Found NOTE: keyword in LLM output at index {note_match.start()}. Cropping output text.")
        answer = answer[:note_match.start()].strip()

    if "User said" in answer:
        try: 
            answer = answer.split("User said")[0]
        except Exception:
            pass

    answer = multi_replace(answer, {"Assistant:": "", "ALFRED:": ""})
    
    # Final safety measure to ensure meaningful output instead of a cut-off mid-sentence.
    if answer and answer[-1] not in ['.', '!', '?', '"', '\'']:
        last_punct = max(answer.rfind('.'), answer.rfind('!'), answer.rfind('?'))
        if last_punct != -1:
            answer = answer[:last_punct+1]
        else:
            answer += "..."
            
    answer = answer.strip()
    logger.info(f"LLM generated answer: '{answer}'")

    MEMORY.add_to_history(prompt, answer)
    return answer
