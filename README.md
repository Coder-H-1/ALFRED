# A.L.F.R.E.D
This is a test chat-based responsive automatic command structured script based on pretrained LLM model.


Its full form I made is:
    
    Automated Learning Framework for Research and Everyday Duties


Inspired by `ALFRED Pennyworth` from `The Dark knight` movie


ABOUT:

*`main.py`* file is the starting file

*`launcher.pyw`* is a hotkey listener and works in background

It uses *`llama_cpp`* for LLM in gguf format


[ALFRED] for _chatting_ is currently using *`OpenHermes-2.5-mistril-7b.Q4_L_M.gguf`*

model link : `https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF/tree/main`

NOTE: Download A Converstional model like above and MOVE it to FILES\model




*PYTHON MODULES* used:

[EXTERNAL]  <-: needs to be installed

[names]
llama-cpp-python, keyboard, pyautogui, speechRecognition, pycaw, pyttsx3, \
vosk, pyaudio, requests, vlc, yt_dlp, screen_brightness_control, dateparser

To download them use:  [CMD/PowerShell]

    pip install llama-cpp-python keyboard pyautogui speechRecognition pycaw pyttsx3 vosk pyaudio requests python-vlc yt_dlp screen_brightness_control

[PRELOADED / INTERNAL] <-: already included in python installation

    os, sys, threading, subprocess, time, json, datetime

Some of the python modules may not work or download like regular ones, for that you can download prebuilt wheels

NOTE: Download the version that matches your Python interpreter


pyaudio : `https://pypi.org/project/PyAudio/#files` \
llama_cpp_python : `https://pypi.org/project/llama-cpp-python/#description`
