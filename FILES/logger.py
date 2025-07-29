import datetime
from FILES.GI_Updater import GUI_UPDATE_obj
def get_str_DateTime() -> list:
    DATE_TIME_24H   = datetime.datetime.now().strftime("%Y-%m-%d > %H:%M:%S")
    DATE  = datetime.datetime.now().strftime("%Y_%m_%d")
    DAY_OF_YEAR     = datetime.datetime.now().strftime("%j")
    YEAR     = datetime.datetime.now().strftime("%Y")

    return [DATE, DATE_TIME_24H, DAY_OF_YEAR, YEAR]

import os,time

Folder = "FILES\\logs\\on_window_logs"
curr_dateTime = get_str_DateTime()
curr_folder = curr_dateTime[2] + "_" + curr_dateTime[3]
curr_filename = f"{Folder}\\{curr_folder}\\{curr_dateTime[0]}.log"

GUI_UPDATE_obj.Update("conf" , curr_filename)

class LOGS:
    def For_file_errors(self) -> None:
        """
        Checks for the logs folder if present [ if not present -> creates them ]
        """

        if not os.path.exists(f"{Folder}"):
            print("True")
            os.makedirs(f"{Folder}")

        if not os.path.exists(f"{Folder}\\{curr_folder}"):
            print("True")
            os.makedirs(f"{Folder}\\{curr_folder}")
        
        if not os.path.exists(f"{curr_filename}"):
            with open(f"{curr_filename}" , "w") as file:
                file.write("")
            print("True")

    def clear_logs() -> bool:
        if os.rmdir("FILES\\logs\\on_window_log") == True: return True
        else: False


    def get_Last_updates(self):
        index:int = 0
        Content = []
        for lines in open(f"{curr_filename}" , "r"):
            
            if index > 4: 
                Content.pop(0)
            
            Content.append(lines)
        
            index+=1
        print(len(Content))
        for line in Content:
            print(line)

    def update(self, function_name:str, value, ret_value=None):
        try:
            with open(f"{curr_filename}" , "a") as Log_file:
                Log_file.write(f"LOG:[{function_name}] - [{curr_dateTime[1]}] >> | {value} | => | {ret_value} |.\n")

        except FileNotFoundError:
            LOGS().For_file_errors()
            LOGS().update(function_name, value, ret_value)


LOG = LOGS()