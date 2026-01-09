
# A HARD coded reminder function
# Only GOD know what is happening


import threading
import time
import json
import os
from datetime import datetime, timedelta
from FILES.util_functions import speak
import dateparser

REMINDERS = []  ## Stores Reminders 
REMINDER_FILE = "FILES\\support\\reminders.json" 

NUM_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50
}

def parse_spoken_time(spoken_text: str):
    spoken_text = spoken_text.lower()
    suffix = ""

    if "am" in spoken_text:
        suffix = "AM"
        spoken_text = spoken_text.replace("am", "")
    elif "pm" in spoken_text:
        suffix = "PM"
        spoken_text = spoken_text.replace("pm", "")

    words = spoken_text.strip().split()

    hour = NUM_WORDS.get(words[0], -1) if len(words) >= 1 else -1
    minute = 0

    if len(words) == 3:
        minute = NUM_WORDS.get(words[1], 0) + NUM_WORDS.get(words[2], 0)
    elif len(words) == 2:
        minute = NUM_WORDS.get(words[1], 0)
    elif len(words) > 3:
        minute = NUM_WORDS.get(words[-2], 0) + NUM_WORDS.get(words[-1], 0)

    if hour != -1 and minute < 60:
        time_string = f"{hour}:{minute:02d} {suffix}".strip()
        parsed = dateparser.parse(time_string)
        if parsed:
            return parsed

    # ➕ Fallback if spoken failed: relative time like "in 10 minutes"
    fallback = dateparser.parse(spoken_text, settings={"PREFER_DATES_FROM": "future"})
    return fallback


def save_reminders():
    with open(REMINDER_FILE, "w") as f:
        json.dump([
            {"task": task, "time": when.strftime("%Y-%m-%d %H:%M:%S")}
            for task, when in REMINDERS
        ], f)

def load_reminders():
    if not os.path.exists(REMINDER_FILE):
        return
    try:
        with open(REMINDER_FILE, "r") as f:
            data = json.load(f)
            for item in data:
                task = item["task"]
                when = datetime.strptime(item["time"], "%Y-%m-%d %H:%M:%S")
                if when > datetime.now():
                    REMINDERS.append((task, when))
    except:
        speak("There was a problem loading saved reminders, sir.")

def set_reminder(task: str, when: datetime):
    REMINDERS.append((task, when))
    save_reminders()

def cancel_reminder(task_or_time: str):
    task_or_time = task_or_time.lower().strip()
    removed = False
    for reminder in REMINDERS[:]:
        task, when = reminder
        if task_or_time in task.lower() or task_or_time in when.strftime('%I:%M %p').lower():
            REMINDERS.remove(reminder)
            removed = True
            speak(f"Cancelled reminder: {task} at {when.strftime('%I:%M %p')}, sir.")
    if removed:
        save_reminders()
    else:
        speak("I'm afraid I couldn't find any matching reminder to cancel, sir.")

def list_reminders():
    if not REMINDERS:
        return "There are no active reminders, sir."
    return "\n".join(
        f"{i+1}. {task} at {when.strftime('%I:%M %p')}" for i, (task, when) in enumerate(REMINDERS)
    )

def reminder_checker():
    while True:
        now = datetime.now()
        for task, when in REMINDERS[:]:
            if now >= when:
                speak(f"Sir, it is time for : {task}")
                REMINDERS.remove((task, when))
                save_reminders()
        time.sleep(30)

def start_background_reminder_thread():
    load_reminders()
    thread = threading.Thread(target=reminder_checker, daemon=True)
    thread.start()
