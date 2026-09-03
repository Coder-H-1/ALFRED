"""
audio_ducker.py — Smart Audio Ducking for ALFRED.

Detects active external audio sessions via pycaw and reduces their volume
by 85% during speech playback. Restores previous volume once speech finishes
or is interrupted.
"""

import os
import threading
import comtypes
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioMeterInformation
from FILES.logger import get_logger

logger = get_logger(__name__)


class AudioDucker:
    """
    Manages intelligent volume ducking for non-ALFRED system audio sessions.
    Reduces external audio by 85% (volume * 0.15) while speech is playing,
    and restores previous volume when speech completes.
    """

    def __init__(self, duck_percent: float = 0.85):
        self.duck_percent = duck_percent
        self.reduction_factor = max(0.0, 1.0 - duck_percent)  # 0.15 for 85% reduction
        self._ducked = False
        self._saved_sessions = []  # list of (session, original_volume)
        self._lock = threading.Lock()

    @property
    def is_ducked(self) -> bool:
        return self._ducked

    def duck(self) -> bool:
        """
        Scans system audio sessions and reduces any active/playing external audio by 85%.
        Leaves ALFRED's process audio untouched.
        Returns True if sessions were ducked.
        """
        with self._lock:
            if self._ducked:
                return True

            comtypes.CoInitialize()
            try:
                current_pid = os.getpid()
                sessions = AudioUtilities.GetAllSessions()
                active_to_duck = []

                for session in sessions:
                    # Never duck ALFRED's own process
                    if session.ProcessId == current_pid:
                        continue

                    v = session.SimpleAudioVolume
                    if not v:
                        continue

                    is_active = False
                    # Check session state (1 == AudioSessionStateActive)
                    if getattr(session, "State", 0) == 1:
                        is_active = True

                    # Also check instantaneous audio peak
                    try:
                        meter = session._ctl.QueryInterface(IAudioMeterInformation)
                        if meter.GetPeakValue() > 0.0001:
                            is_active = True
                    except Exception:
                        pass

                    if is_active:
                        active_to_duck.append(session)

                if not active_to_duck:
                    logger.debug("Smart Speech: No active other audio found to duck.")
                    return False

                self._saved_sessions = []
                for session in active_to_duck:
                    try:
                        v = session.SimpleAudioVolume
                        orig_vol = v.GetMasterVolume()
                        if orig_vol > 0.001:
                            ducked_vol = max(0.0, orig_vol * self.reduction_factor)
                            v.SetMasterVolume(ducked_vol, None)
                            self._saved_sessions.append((session, orig_vol))
                            pname = session.Process.name() if session.Process else "System"
                            logger.info(
                                f"Smart Speech: Ducked {pname} audio by 85% "
                                f"(from {orig_vol:.2f} to {ducked_vol:.2f})"
                            )
                    except Exception as e:
                        logger.warning(f"Smart Speech: Failed to duck audio session: {e}")

                if self._saved_sessions:
                    self._ducked = True
                    return True
                return False

            except Exception as e:
                logger.error(f"Smart Speech: Error during audio ducking: {e}", exc_info=True)
                return False
            finally:
                comtypes.CoUninitialize()

    def restore(self) -> None:
        """
        Restores all previously ducked audio sessions back to their original volumes.
        """
        with self._lock:
            if not self._ducked:
                return

            comtypes.CoInitialize()
            try:
                for session, orig_vol in self._saved_sessions:
                    try:
                        v = session.SimpleAudioVolume
                        if v:
                            v.SetMasterVolume(orig_vol, None)
                            pname = session.Process.name() if session.Process else "System"
                            logger.info(
                                f"Smart Speech: Restored {pname} audio to original volume ({orig_vol:.2f})"
                            )
                    except Exception as e:
                        logger.warning(f"Smart Speech: Failed to restore session volume: {e}")
            except Exception as e:
                logger.error(f"Smart Speech: Error restoring ducked audio: {e}", exc_info=True)
            finally:
                self._saved_sessions = []
                self._ducked = False
                comtypes.CoUninitialize()
