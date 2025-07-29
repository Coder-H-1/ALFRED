CONFIG_FILE = "FILES\\support\\Graphical_Interface\\config.file"

import os,time

class Update_GI:
    def __init__(self):
        self.Content = [] # new contents

    def _update_file(self, content:str) -> None:
        with open(f"{CONFIG_FILE}" , "w") as File:
            File.write(content)
    
    def old_contents() -> list: 
        return [lines for lines in open(f"{CONFIG_FILE}" , "r")]

    def get_Value(self, name:str, value) -> None:
        old_Content:list = Update_GI.old_contents()

        if "speak" in name:
            for items in old_Content:
                if "speak" in items or "listen" in items:
                    continue
                else:
                    if items not in self.Content:
                        if "speak" in items or "listen" in items:continue
                        else:
                            self.Content.append(items)   
                    else:pass    

            if "true" in value or "True" in value:
                self.Content.append("is_speaking : true\nis_listening : false\n")
            else:
                self.Content.append("is_speaking : false\nis_listening : true\n")


        if "conf" in name:
            
            if os.path.exists(f"{value}"):
                string = f"LOG_path : {value}"
                try:
                    index = 0
                    for i , line in enumerate(self.Content):
                        if "LOG_path" in line:
                            index = int(i)
                            self.Content.pop(index)

                            self.Content.append(string)
                            break
                         
                except:
                    index = 0
                    for j, lines in enumerate(old_Content):
                        if "LOG_path" in lines:
                            index = int(j)

                            old_Content.pop(index)
                            self.Content.append(string)
                            break


    def Update(self, element_name:str, value:str):
        self.get_Value(element_name, value)

        stringContents = ""
        for i in self.Content:
            stringContents += i

        self._update_file(stringContents)


GUI_UPDATE_obj = Update_GI()
