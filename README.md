# A.L.F.R.E.D

**Automated Logistics for Facilitating Resources and Executive Duties**

A.L.F.R.E.D is a chat-based, responsive, command-structured automation system powered by locally running pretrained Large Language Models (LLMs). It is designed to function as a background assistant capable of understanding natural language commands and executing system-level actions on Windows.

---

### 📌 Project Overview

A.L.F.R.E.D acts as an intelligent automation layer between the user and the operating system. It combines LLM inference, speech recognition, system control, and hotkey-based background execution into a single cohesive workflow.

The project runs entirely locally using GGUF-format models via `llama_cpp`, ensuring privacy and offline functionality.

---

## Key Features

1. **Local LLM Conversations**: Integrates with `llama.cpp` to run local LLaMA GGUF models for private, low-latency conversational responses. Includes dynamic elastic text generation to prevent sentence cut-offs.
2. **Multi-threaded Voice Output**: Leverages [Kyutai's Pocket TTS](https://github.com/kyutai-labs/pocket-tts) model on CPU with sequential playback queueing to deliver high-quality text-to-speech output without blocking main loops.
3. **Voice & Type Inputs**: Speech recognition parses commands via Google STT, with terminal text input support.
4. **Persistent Memory System**: Combines short-term RAM caching of conversation context with a long-term SQLite database using FTS5 (Full-Text Search) and automatic tagging to recall, search, or forget past conversations.
5. **System Automation**: Native desktop control interfaces to adjust volume (via `pycaw`), screen brightness, open/close applications (Notepad, Command Prompt, Chrome, WhatsApp, IDEs), toggle system settings, restart, or shutdown.
6. **Model Context Protocol (MCP) Intermediary Bridge**: Connects ALFRED to the Octopus MCP engine using a dedicated async daemon and synchronous facade, supporting fast-path keyword routing, local Qwen tool classification, and standard stdio external tools.
7. **Real-time Resource Monitoring**: Integrated CPU/RAM stats collector for system status feedback and voice status responses.
8. **Thread-Safe Daily Latency Profiling**: Automatically tracks execution latency across all core functions with high-precision sub-second tracking, daily file segregation, exit grouping by function, and summary metrics.
9. **Native Log Compression & Archiving**: Custom binary compression (`.compressed_logs` with magic header `ALF1`, CRC32 validation, and zlib level 9 compression) for rotated daily logs and latency traces.
10. **Environment Hardening**: All backend routing connections are dynamically resolved through `.env` configurations.
11. **Smart Audio Ducking**: Automatically detects external audio streams via `pycaw` and ducks volume by 85% during ALFRED speech playback, seamlessly restoring volume upon completion or voice interrupt.

---

## File Structure

The project layout organizes files systematically across frontend, plugins framework, and core Python modules:

```
Project/
├── .env                  # Local environment configurations (ignored by git)
├── .gitignore            # Git exclusion guidelines
├── alfred_voice.py       # Multi-threaded Pocket-TTS synthesis module with voice interrupt
├── launcher.pyw          # Background service hotkey and health check poller
├── LICENSE               # MIT License
├── main.py               # Main application entry point
├── README.md             # Project documentation
├── requirements.txt      # Python dependencies manifest
├── update_report.md      # Detailed research and architecture update report
├── version.py            # Project constants and network metadata
├── Data/                 # Application data and logs
├── FILES/                # Core Python modules
│   ├── audio_ducker.py   # Smart volume ducking for background audio during speech
│   ├── command_components/ # Modular system command subroutines
│   │   ├── app_launcher.py      # App launch and process lifecycle
│   │   ├── log_commands.py      # Log viewer and compression triggers
│   │   ├── memory_commands.py   # LTM recall, search, and forget commands
│   │   ├── search.py            # Google and web queries
│   │   ├── system_status.py     # Battery, CPU, RAM metrics
│   │   └── weather_commands.py  # Weather updates
│   ├── commands.py       # Core mapped system command routines
│   ├── intent.py         # Experimental intent classifier / BERT trainer
│   ├── LATENCY_RECORDER.py # Thread-safe file-based latency profiler & CLI
│   ├── log_compressor.py # Custom binary log compressor (.compressed_logs)
│   ├── logger.py         # Centralized timed rotating daily log handler
│   ├── long_term_memory.py # Standalone SQLite conversation memory database
│   ├── memory.py         # RAM cache / LTM integration layer
│   ├── model_manager.py  # Loader / unloader for local GGUF models
│   ├── plugin_host.py    # Octopus Model Context Protocol (MCP) Bridge adapter
│   ├── resource_monitor.py # System CPU/RAM tracking module
│   ├── system_control.py # Pycaw volume / Screen-brightness control routines
│   ├── turbo_quant.py    # TurboQuant vector quantization engine
│   ├── util_functions.py # Multi-replace, search tools, microphone listener
│   ├── utils.py          # LLaMA responder loop interface
│   ├── web_search_extractor.py # Web search extractor
│   ├── window_manager.py # pygetwindow layout helper static class
│   └── youtube_player.py # yt-dlp resilient search and stream extraction
├── FmWk/                 # Octopus Model Context Protocol (MCP) framework (external repo)
└── research/             # MCP deep research and tool development guides
```

---

## Basic Principles

- **Optimal Reusability**: Common helpers such as string replacement and sound synthesis are centralized under `FILES/util_functions.py` and `alfred_voice.py`.
- **Zero-Hardcoding**: Endpoints like `OpenWeatherKey` are sourced dynamically from `.env`.
- **Structured Operations Logging**: Every module utilizes a centralized logger in `FILES/logger.py` writing rotating logs to `logs/alfred.log` at the `DEBUG` level while displaying essential information to the console.
- **Detachable Ecosystem**: The `FmWk/` directory represents a fully decoupled microservice structure with its own git history. It communicates with the main workspace solely via network requests and standard socket protocols.

---

## Workflow of the Project

```mermaid
flowchart TD
    Launcher[launcher.pyw background poller] -->|alt+shift+a+s+d| Launch[Start main.py]
    Launch --> InitTTS[Initialize pocket-tts & load models]
    Launch --> StartSocket[Start plugin listener on port 65432]
    
    StartSocket --> Loop[Listen Loop]
    Loop --> Input{Input Command}
    Input -->|Voice| Speech[sr.Recognizer / Google STT]
    Input -->|Type| ConsoleInput[Terminal console input]
    
    Speech --> Process[process_command matching]
    ConsoleInput --> Process
    
    Process -->|1. Switch Mode| Toggle[Toggle type/voice input mode]
    Process -->|2. Exit/Restart| Terminate[Save memory and exit sys]
    Process -->|3. Plugins match| PluginRun[Execute dynamically hot-loaded script]
    Process -->|4. Hardcoded actions| SysAction[Run system control/app/weather action]
    Process -->|5. General conversation| LLMResponse[Prompt LLaMA responder]
    
    SysAction --> Speak[Synthesize Response and Speak]
    PluginRun --> Speak
    LLMResponse --> Speak
    
    Speak --> SaveMem[Save to short-term cache & LTM SQLite db]
    SaveMem --> Loop
```

---

## Setup & Execution

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Installation
Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Config
Create a `.env` file in the root directory:
```env
OpenWeatherKey=your-openweather-api-key
```

### 4. Run Launcher
To run ALFRED in the background:
```bash
pythonw launcher.pyw
```
Press `alt+shift+a+s` followed by `d` to summon the interface.

To run the application directly in terminal mode:
```bash
python main.py
```

---

## System Logging & Latency Tracking

### 1. Operations Logging
All application executions, requests, socket connections, and exceptions are logged to:
- Console outputs
- **`logs/alfred.log`** (Rotates daily, retains last 7 days of debug logs)
- Rotated logs are automatically compressed to `.compressed_logs` on shutdown via `FILES/log_compressor.py`.

### 2. Latency Profiler & CLI
Latency is captured on a per-call basis via the `@track_latency` decorator and written to `logs/latency/YYYY-MM-DD.log`. On application shutdown (`atexit`), logs are automatically reorganized by function name, annotated with summary statistics, and compressed.

Inspect latency metrics via the CLI:
```bash
# Decompress and show first 50 lines of a specific date
python .\FILES\LATENCY_RECORDER.py --show 2026-09-01

# Limit number of lines displayed
python .\FILES\LATENCY_RECORDER.py --show 2026-09-01 --lines 20

# Filter records and summaries for a specific function
python .\FILES\LATENCY_RECORDER.py --show 2026-09-01 --function-name commands.process_command

# List all available recorded dates and archive sizes
python .\FILES\LATENCY_RECORDER.py --list

# Clean up records older than 15 days
python .\FILES\LATENCY_RECORDER.py --clean
```

---

### 💻 System Requirements (Tested On)

- **Operating System**: Windows
- **Python Version**: Python 3.12.6 (64-bit)
- **Architecture**: x86-64 CPU (no GPU required)

---

### ⚠️ Disclaimer

This project is intended for educational and experimental purposes. Users are responsible for the commands executed by the system.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
