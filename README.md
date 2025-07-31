# A.L.F.R.E.D

This is a test chat-based responsive automatic command structured script based on pretrained LLM model.

Inspired by `ALFRED Pennyworth` from `The Dark knight` movie

Made Using => Python 3.12.6 64bit

ABOUT:

*`main.py`* file is the starting file

*`launcher.pyw`* is a hotkey listener and works in background



USES =>  *`llama_cpp`* for LLM in gguf format \
     =>  *`OpenHermes-2.5-mistril-7b.Q4_L_M.gguf`* (about 4.6 GB file) | due to low specs => 8GB RAM


model link => `https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF/tree/main`


NOTE : Download A Converstional model like above and *move* it to `FILES\model`



*PYTHON MODULES* used:

FOR => WINDOWS Python 3.12.6 x86-64 architecture CPU:

*Names of modules*
    llama-cpp-python, keyboard, pyautogui, speechRecognition, pycaw, pyttsx3, \
    vosk, pyaudio, requests, vlc, yt_dlp, screen_brightness_control, dateparser


To download them use:  [CMD/PowerShell]


    pip install keyboard pyautogui speechRecognition pycaw pyttsx3 vosk requests python-vlc yt_dlp screen_brightness_control dateparser


For `llama-cpp-python` and `pyaudio` if you are getting an CMAKE error or something else :

    pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --prefer-binary
    
    pip install llama-cpp-python --extra-index-url https://files.pythonhosted.org/packages/b0/6a/d25812e5f79f06285767ec607b39149d02aa3b31d50c2269768f48768930/PyAudio-0.2.14-cp312-cp312-win_amd64.whl 
    

[PRELOADED / INTERNAL] <-: already included in python installation

    os, sys, threading, subprocess, time, json, datetime

