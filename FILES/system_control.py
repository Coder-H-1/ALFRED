# system_control.py

import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import POINTER, cast
from comtypes import CLSCTX_ALL

def set_brightness(percent: int):
    try:
        sbc.set_brightness(percent)
        return f"Brightness set to {percent}%, sir."
    except Exception as e:
        return f"I'm afraid I couldn't set brightness, sir. Error: {e}"

def adjust_brightness(direction: str):
    current = sbc.get_brightness()[0]
    delta = 10 if direction == "increase" else -10
    new_brightness = max(0, min(100, current + delta))
    return set_brightness(new_brightness)

def set_volume(percent: int):
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
        return f"Volume set to {percent}%, sir."
    except Exception as e:
        return f"I couldn't set volume, sir. Error: {e}"

def adjust_volume(direction: str):
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current = volume.GetMasterVolumeLevelScalar() * 100
        delta = 10 if direction == "increase" else -10
        new_volume = max(0, min(100, current + delta))
        return set_volume(int(new_volume))
    except Exception as e:
        return f"I couldn't adjust volume, sir. Error: {e}"

def mute_volume():
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMute(1, None)
        return "System muted, sir."
    except Exception as e:
        return f"I couldn't mute the volume, sir. Error: {e}"
