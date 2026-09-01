from FILES.gui_controller import move_window, pin_window, hide_all
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

BOX_MAPPING = {
    "answer": "answerBox", 
    "response": "answerBox", 
    "preview": "showBox", 
    "show": "showBox", 
    "log": "logs", 
    "logs": "logs", 
    "process": "functionCalls"
}

ZONE_MAPPING = {
    "focus": "focus", 
    "active": "active", 
    "passive": "passive", 
    "rapid": "rapid"
}

@track_latency("commands.process_command.move_window")
def handle_move_window(command: str) -> str:
    words = command.split()
    box_name = None
    zone_name = None
    for w in words:
        if w in BOX_MAPPING: box_name = BOX_MAPPING[w]
        if w in ZONE_MAPPING: zone_name = ZONE_MAPPING[w]
    
    if box_name and zone_name:
        logger.info(f"Moving window {box_name} to {zone_name}")
        if move_window(box_name, zone_name):
            return f"Moved {box_name} to the {zone_name} zone, sir."
    return "I didn't quite catch which window to move where, sir."

@track_latency("commands.process_command.pin_window")
def handle_pin_window(command: str) -> str:
    words = command.split()
    box_name = None
    for w in words:
        if w in BOX_MAPPING: box_name = BOX_MAPPING[w]
    
    if box_name:
        logger.info(f"Pinning window {box_name}")
        if pin_window(box_name, True):
            return f"Pinned {box_name}, sir."
    return "I didn't catch which window to pin."

@track_latency("commands.process_command.unpin_window")
def handle_unpin_window(command: str) -> str:
    words = command.split()
    box_name = None
    for w in words:
        if w in BOX_MAPPING: box_name = BOX_MAPPING[w]
    
    if box_name:
        logger.info(f"Unpinning window {box_name}")
        if pin_window(box_name, False):
            return f"Unpinned {box_name}, sir."
    return "I didn't catch which window to unpin."

@track_latency("commands.process_command.clean_gui")
def handle_clean_gui(command: str) -> str:
    logger.info("Clearing GUI screen")
    hide_all()
    return "The screen has been cleared, sir."
