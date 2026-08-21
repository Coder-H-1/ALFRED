# system_control.py

import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import POINTER, cast
from comtypes import CLSCTX_ALL
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

_volume_interface = None

@track_latency("system_control._get_volume")
def _get_volume():
    global _volume_interface
    if not _volume_interface:
        logger.debug("Activating system Audio speakers via pycaw...")
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            _volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
        except Exception as e:
            logger.error(f"Failed to activate speaker interface: {e}", exc_info=True)
            raise
    return _volume_interface

@track_latency("system_control.set_brightness")
def set_brightness(percent: int) -> str:
    try:
        logger.info(f"Setting brightness to: {percent}%")
        sbc.set_brightness(percent)
        return f"Brightness set to {percent}%, sir."
    except Exception as e:
        logger.error(f"Failed to set system brightness: {e}", exc_info=True)
        return "I'm afraid I couldn't set brightness, sir."

@track_latency("system_control.adjust_brightness")
def adjust_brightness(direction: str) -> str:
    try:
        current = sbc.get_brightness()[0]
        delta = 10 if direction == "increase" else -10
        new_brightness = max(0, min(100, current + delta))
        logger.info(f"Adjusting brightness direction: '{direction}' (current: {current}%, new: {new_brightness}%)")
        return set_brightness(new_brightness)
    except Exception as e:
        logger.error(f"Failed to adjust system brightness: {e}", exc_info=True)
        return "I'm afraid I couldn't adjust brightness, sir."

@track_latency("system_control.set_volume")
def set_volume(percent: int) -> str:
    try:
        logger.info(f"Setting volume to: {percent}%")
        volume = _get_volume()
        volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
        return f"Volume set to {percent}%, sir."
    except Exception as e:
        logger.error(f"Failed to set system volume: {e}", exc_info=True)
        return f"I couldn't set volume, sir. Error: {e}"

@track_latency("system_control.adjust_volume")
def adjust_volume(direction: str) -> str:
    try:
        volume = _get_volume()
        current = volume.GetMasterVolumeLevelScalar() * 100
        delta = 10 if direction == "increase" else -10
        new_volume = max(0, min(100, current + delta))
        logger.info(f"Adjusting volume direction: '{direction}' (current: {int(current)}%, new: {int(new_volume)}%)")
        return set_volume(int(new_volume))
    except Exception as e:
        logger.error(f"Failed to adjust system volume: {e}", exc_info=True)
        return f"I couldn't adjust volume, sir. Error: {e}"

@track_latency("system_control.mute_volume")
def mute_volume() -> str:
    try:
        logger.info("Muting system volume")
        volume = _get_volume()
        volume.SetMute(1, None)
        return "System muted, sir."
    except Exception as e:
        logger.error(f"Failed to mute system volume: {e}", exc_info=True)
        return f"I couldn't mute the volume, sir. Error: {e}"
