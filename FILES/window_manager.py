
################
## For Windows ##
import win32gui
import win32con
################

import pygetwindow as gw

class Window:   ### window manager for Windows
    def __init__(self, window_name:str, brin_on_front:bool=True) -> None:
            self.window_name = f"{window_name}"
            self.Window = gw.getWindowsWithTitle(f"{self.window_name}")[0]

            if brin_on_front == True:
                  self.brin_on_front()  

    def brin_on_front(self) -> None:  ### Brings selected window to front
            self.Window.activate()

    def resize(self, x:int, y:int) -> None:  ### Resizes the selected window
            self.Window.resizeTo(int(x), int(y))

    def move_to(self, x:int, y:int) -> None:    ### Moves the selected window
            self.Window.moveTo(int(x), int(y))

    

    def Window_Manage(window_name : str, window_size: tuple|None) -> bool:
        """
        Manages the location and size of the selected window\n
        parameters\n
        window_name:str -> Name of the selected window\n   
    
        window_size:tuple -> (x, y, width, height)\n
            | x, y -> x and y coordinates of windows |\n
            | width, height -> size of window        |\n
        """
        hwnd = win32gui.FindWindow(None, window_name) 
    
        if hwnd:
            # Get current window position and dimensions
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            # Move and resize the window
    
            x, y, width, height = window_size
    
            # Arguments: hwnd, x, y, width, height, repaint
            win32gui.MoveWindow(hwnd, x, y , width, height, False) 
    
            # Minimize the window
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    
            # Maximize the window
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    
            # Restore the window
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return True
        else:
            print("Window not found.")
            return False
        
    
    