import json
import os
from FILES.LATENCY_RECORDER import track_latency

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
LAYOUT_PATH = os.path.join(DATA_DIR, "layout_state.json")

@track_latency("gui_controller.init_config")
def init_config():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    # Initialize layout if it doesn't exist
    if not os.path.exists(LAYOUT_PATH):
        layout = {
            "answerBox": { "zone": "focus", "pinned": False },
            "showBox": { "zone": "focus", "pinned": False },
            "logs": { "zone": "passive", "pinned": False },
            "functionCalls": { "zone": "rapid", "pinned": False },
            "visualizer": { "zone": "rapid", "pinned": False }
        }
        with open(LAYOUT_PATH, "w") as f:
            json.dump(layout, f, indent=4)
            
    if not os.path.exists(CONFIG_PATH):
        reset_gui()

@track_latency("gui_controller.get_layout")
def get_layout():
    try:
        with open(LAYOUT_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "answerBox": { "zone": "focus", "pinned": False },
            "showBox": { "zone": "focus", "pinned": False },
            "logs": { "zone": "passive", "pinned": False },
            "functionCalls": { "zone": "rapid", "pinned": False },
            "visualizer": { "zone": "rapid", "pinned": False }
        }

@track_latency("gui_controller.save_layout")
def save_layout(layout):
    with open(LAYOUT_PATH, "w") as f:
        json.dump(layout, f, indent=4)

@track_latency("gui_controller.read_config")
def read_config():
    layout = get_layout()
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            
            # Ensure new keys are present
            if "commandInput" not in data:
                data["commandInput"] = False
                data["statusText"] = ""
            if "videoControls" not in data:
                data["videoControls"] = {"muted": False, "audioOnly": False, "seekOffset": 0, "seekDirection": None}
            if "errors" not in data:
                data["errors"] = {"visible": False, "text": "", "zone": "update"}
                
            # Inject zone information from layout
            if "showBox" in data: data["showBox"]["zone"] = layout.get("showBox", {}).get("zone", "focus")
            if "answerBox" in data: data["answerBox"]["zone"] = layout.get("answerBox", {}).get("zone", "focus")
            if "logs" in data: data["logs"]["zone"] = layout.get("logs", {}).get("zone", "passive")
            if "functionCalls" in data: data["functionCalls"]["zone"] = layout.get("functionCalls", {}).get("zone", "rapid")
            data["visualizer"] = {"zone": layout.get("visualizer", {}).get("zone", "rapid")}
            
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "showBox": { "visible": False, "data": [], "zone": layout.get("showBox", {}).get("zone", "focus") },
            "answerBox": { "visible": False, "text": "", "zone": layout.get("answerBox", {}).get("zone", "focus") },
            "logs": { "visible": False, "text": "", "zone": layout.get("logs", {}).get("zone", "passive") },
            "functionCalls": { "visible": False, "calls": [], "zone": layout.get("functionCalls", {}).get("zone", "rapid") },
            "visualizer": { "zone": layout.get("visualizer", {}).get("zone", "rapid") },
            "errors": { "visible": False, "text": "", "zone": "update" },
            "queryActive": False,
            "commandInput": False,
            "statusText": "",
            "videoControls": {"muted": False, "audioOnly": False, "seekOffset": 0, "seekDirection": None}
        }

@track_latency("gui_controller.write_config")
def write_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)

@track_latency("gui_controller.reset_gui")
def reset_gui():
    layout = get_layout()
    write_config({
        "showBox": { "visible": False, "data": [], "zone": layout.get("showBox", {}).get("zone", "focus") },
        "answerBox": { "visible": False, "text": "", "zone": layout.get("answerBox", {}).get("zone", "focus") },
        "logs": { "visible": False, "text": "", "zone": layout.get("logs", {}).get("zone", "passive") },
        "functionCalls": { "visible": False, "calls": [], "zone": layout.get("functionCalls", {}).get("zone", "rapid") },
        "visualizer": { "zone": layout.get("visualizer", {}).get("zone", "rapid") },
        "errors": { "visible": False, "text": "", "zone": "update" },
        "queryActive": False,
        "commandInput": False,
        "statusText": "",
        "videoControls": {"muted": False, "audioOnly": False, "seekOffset": 0, "seekDirection": None}
    })

@track_latency("gui_controller.set_query_active")
def set_query_active(active: bool):
    data = read_config()
    data["queryActive"] = active
    if active:
        data["logs"]["visible"] = False
        data["logs"]["text"] = ""
        data["functionCalls"]["visible"] = False
        data["functionCalls"]["calls"] = []
        if data["answerBox"].get("text"):
            if not data["answerBox"]["text"].endswith("\n"):
                data["answerBox"]["text"] += "\n\n"
    write_config(data)

@track_latency("gui_controller.add_function_call")
def add_function_call(func_name: str):
    data = read_config()
    data["functionCalls"]["visible"] = True
    data["functionCalls"]["calls"].append(func_name)
    write_config(data)

@track_latency("gui_controller.show_answer")
def show_answer(text: str):
    data = read_config()
    layout = get_layout()
    
    # Auto-movement logic: if showBox is visible with media, and answerBox is in focus and not pinned, move it to active
    if data["showBox"]["visible"] and layout["answerBox"]["zone"] == "focus" and not layout["answerBox"]["pinned"]:
        layout["answerBox"]["zone"] = "active"
        save_layout(layout)
        data["answerBox"]["zone"] = "active"
        
    data["answerBox"]["visible"] = True
    if not data["answerBox"].get("text"):
        data["answerBox"]["text"] = text
    else:
        data["answerBox"]["text"] += " " + text
    write_config(data)

@track_latency("gui_controller.show_logs")
def show_logs(text: str):
    data = read_config()
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    formatted_log = f"[{timestamp}] {text}\n"
    data["logs"]["visible"] = True
    if "text" not in data["logs"]:
        data["logs"]["text"] = ""
    data["logs"]["text"] += formatted_log
    write_config(data)

@track_latency("gui_controller.show_data")
def show_data(images_or_data: list):
    data = read_config()
    layout = get_layout()
    
    # Priority movement: showBox goes to focus
    if layout["showBox"]["zone"] != "focus" and not layout["showBox"]["pinned"]:
        layout["showBox"]["zone"] = "focus"
        
    # If answerBox is in focus and not pinned, move it out to active
    if layout["answerBox"]["zone"] == "focus" and not layout["answerBox"]["pinned"]:
        layout["answerBox"]["zone"] = "active"
        
    save_layout(layout)
    data["showBox"]["zone"] = layout["showBox"]["zone"]
    data["answerBox"]["zone"] = layout["answerBox"]["zone"]
    
    data["showBox"]["visible"] = True
    data["showBox"]["data"] = images_or_data
    write_config(data)

@track_latency("gui_controller.hide_all")
def hide_all():
    reset_gui()

@track_latency("gui_controller.hide_transient_boxes")
def hide_transient_boxes():
    data = read_config()
    data["showBox"]["visible"] = False
    
    layout = get_layout()
    if layout["answerBox"]["zone"] == "active" and not layout["answerBox"]["pinned"]:
        layout["answerBox"]["zone"] = "focus"
        save_layout(layout)
        data["answerBox"]["zone"] = "focus"
        
    data["logs"]["visible"] = False
    data["functionCalls"]["visible"] = False
    data["queryActive"] = False
    data["errors"]["visible"] = False
    write_config(data)

@track_latency("gui_controller.set_input_mode")
def set_input_mode(mode: bool, status_text: str = ""):
    data = read_config()
    data["commandInput"] = mode
    data["statusText"] = status_text
    write_config(data)

@track_latency("gui_controller.read_gui_command")
def read_gui_command() -> str:
    cmd_path = os.path.join(DATA_DIR, "command.txt")
    if os.path.exists(cmd_path):
        with open(cmd_path, "r") as f:
            text = f.read().strip()
        if text:
            with open(cmd_path, "w") as f:
                f.write("")
            return text
    return None

@track_latency("gui_controller.show_error")
def show_error(text: str):
    data = read_config()
    data["errors"]["visible"] = True
    data["errors"]["text"] = text
    write_config(data)

@track_latency("gui_controller.move_window")
def move_window(box_name: str, target_zone: str):
    layout = get_layout()
    if box_name in layout:
        layout[box_name]["zone"] = target_zone
        save_layout(layout)
        data = read_config() # Updates injected zones
        write_config(data)
        return True
    return False

@track_latency("gui_controller.pin_window")
def pin_window(box_name: str, pin: bool):
    layout = get_layout()
    if box_name in layout:
        layout[box_name]["pinned"] = pin
        save_layout(layout)
        return True
    return False

@track_latency("gui_controller.set_video_control")
def set_video_control(action: str, value=None):
    data = read_config()
    if "videoControls" not in data:
        data["videoControls"] = {"muted": False, "audioOnly": False, "seekOffset": 0, "seekDirection": None}
    
    if action == "audio_only":
        data["videoControls"]["audioOnly"] = True
    elif action == "show_video":
        data["videoControls"]["audioOnly"] = False
    elif action == "mute":
        data["videoControls"]["muted"] = True
    elif action == "unmute":
        data["videoControls"]["muted"] = False
    elif action == "rewind":
        data["videoControls"]["seekOffset"] = value
        data["videoControls"]["seekDirection"] = "back"
    elif action == "forward":
        data["videoControls"]["seekOffset"] = value
        data["videoControls"]["seekDirection"] = "forward"
    
    write_config(data)

