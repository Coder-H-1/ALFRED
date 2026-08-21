import win32gui
import win32con
import pygetwindow as gw
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

class Window:
    """Window manager for Windows OS."""
    
    def __init__(self, window_name: str, bring_on_front: bool = True) -> None:
        self.window_name = f"{window_name}"
        logger.info(f"Initializing Window controller for: '{self.window_name}'")
        try:
            self.Window = gw.getWindowsWithTitle(f"{self.window_name}")[0]
            if bring_on_front:
                self.bring_to_front()
        except IndexError:
            logger.warning(f"No window found with title containing: '{self.window_name}'")
            raise RuntimeError(f"Window '{self.window_name}' not found.")

    @track_latency("Window.bring_to_front")
    def bring_to_front(self) -> None:
        """Brings selected window to front."""
        logger.debug(f"Activating window: '{self.window_name}'")
        try:
            self.Window.activate()
        except Exception as e:
            logger.error(f"Failed to activate window '{self.window_name}': {e}")

    @track_latency("Window.resize")
    def resize(self, x: int, y: int) -> None:
        """Resizes the selected window."""
        logger.info(f"Resizing window '{self.window_name}' to width: {x}, height: {y}")
        try:
            self.Window.resizeTo(int(x), int(y))
        except Exception as e:
            logger.error(f"Failed to resize window '{self.window_name}': {e}")

    @track_latency("Window.move_to")
    def move_to(self, x: int, y: int) -> None:
        """Moves the selected window."""
        logger.info(f"Moving window '{self.window_name}' to x: {x}, y: {y}")
        try:
            self.Window.moveTo(int(x), int(y))
        except Exception as e:
            logger.error(f"Failed to move window '{self.window_name}': {e}")

    @staticmethod
    def Window_Manage(window_name: str, window_size: tuple | None) -> bool:
        """
        Manages the location and size of the selected window.
        
        Parameters:
            window_name: Name of the selected window
            window_size: (x, y, width, height) coordinates and dimensions
        """
        logger.info(f"Managing window state for '{window_name}' with specs: {window_size}")
        hwnd = win32gui.FindWindow(None, window_name) 
    
        if hwnd:
            try:
                if window_size:
                    x, y, width, height = window_size
                    win32gui.MoveWindow(hwnd, x, y, width, height, False) 
            
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                logger.info(f"Successfully managed window: '{window_name}'")
                return True
            except Exception as e:
                logger.error(f"Error managing window '{window_name}': {e}", exc_info=True)
                return False
        else:
            logger.warning(f"Window '{window_name}' not found by win32gui.")
            return False