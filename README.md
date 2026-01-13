# A.L.F.R.E.D  
**Automated Limited Functionality Responsive Educational Development (system). or A.L.F.R.E.D.**

A.L.F.R.E.D is a chat-based, responsive, command-structured automation system powered by locally running pretrained Large Language Models (LLMs).  
It is designed to function as a background assistant capable of understanding natural language commands and executing system-level actions on Windows.

Name inspired by **Alfred Pennyworth** from *The Dark Knight*.

---

## 📌 Project Overview

A.L.F.R.E.D acts as an intelligent automation layer between the user and the operating system.  
It combines LLM inference, speech recognition, system control, and hotkey-based background execution into a single cohesive workflow.

The project runs entirely locally using GGUF-format models via `llama_cpp`, ensuring privacy and offline functionality.

---

## 🧠 Key Capabilities

- Chat-based command interpretation using local LLMs  
- Background execution with hotkey triggers  
- Speech recognition and text-to-speech support  
- System automation (keyboard, mouse, volume, brightness, media, etc.)  
- Media playback and YouTube downloading  
- Date and time parsing for contextual commands  
- Modular Python-based architecture  

---

## 📂 Project Structure

    A.L.F.R.E.D/
    │
    ├── main.py # Primary application entry point
    ├── launcher.pyw # Background hotkey listener (runs silently)
    │
    ├── FILES/
    │ └── model/ # Place downloaded GGUF models here
    │
    └── README.md


---

## 🚀 Entry Points

- **main.py**  
  The main execution file. Initializes the LLM, handles command parsing, and executes actions.

- **launcher.pyw**  
  Runs in the background as a hotkey listener and launches A.L.F.R.E.D without opening a console window.

---

## 🤖 Supported LLM Models

The project uses GGUF-format models with `llama_cpp`.

### Pre-tested Models

- **OpenHermes-2.5-Mistral-7B (Q4_K_M)**  
  ~4.6 GB  
  https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF

- **L3.1 Dark Planet – SpinFire Uncensored 8B (Q4_K_M)**  
  ~4.9 GB  
  https://huggingface.co/DavidAU/L3.1-Dark-Planet-SpinFire-Uncensored-8B-GGUF

- **Self Fine-Tuned Qwen2.5-0.5B-Instruct (GGUF)**  
  Converted from the base model:  
  https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct

> **Important:**  
> Download a conversational GGUF model and move it to:
    FILES/model/


---

## 🛠️ System Requirements

- **Operating System:** Windows  
- **Python Version:** Python 3.12.6 (64-bit)  
- **Architecture:** x86-64 CPU (no GPU required)

---

## 📦 Python Dependencies

### Core Modules Used

    llama-cpp-python    
    keyboard
    pyautogui
    win32gui
    plyer
    speechRecognition
    pycaw
    pyttsx3
    vosk
    pyaudio
    requests
    python-vlc
    yt_dlp
    screen_brightness_control
    dateparser

---

## 📥 Installation

### Standard Installation (CMD / PowerShell)

    pip install keyboard plyer pyautogui speechRecognition torch transformers win32gui pycaw pyttsx3 requests python-vlc yt_dlp screen_brightness_control dateparser

---

### llama-cpp-python (CPU-only, prebuilt wheels)

If you encounter CMake or build errors:

    pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --prefer-binary

---

### PyAudio (Windows Python 3.12)

    pip install pyaudio --extra-index-url https://files.pythonhosted.org/packages/b0/6a/d25812e5f79f06285767ec607b39149d02aa3b31d50c2269768f48768930/PyAudio-0.2.14-cp312-cp312-win_amd64.whl

---

## 🧩 Built-in Python Modules

The following modules are preloaded with Python:

    os
    sys
    threading
    subprocess
    time
    json
    datetime


---

## 🔐 Privacy & Offline Usage

- All inference is performed locally  
- No external APIs are required  
- No telemetry or cloud dependency  
- Fully offline after model download  

---

## 📖 Inspiration

> “Some men just want to watch the world burn.”  
> — Alfred Pennyworth, *The Dark Knight*

**A.L.F.R.E.D** is built as a personal automation assistant—quiet, efficient, and always ready in the background.

---

## ⚠️ Disclaimer

This project is intended for educational and experimental purposes.  
Users are responsible for the commands executed by the system.

---

## 📌 Status

    Active Development / Experimental
