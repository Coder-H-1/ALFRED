import os,sys

class Work:
    def __init__(self, filepath:str):
        self.content = []
        self.path = str(filepath)
        self.readFile()

    def readFile(self) -> list:
        if os.path.exists(f"{self.path}"):
            Content = []
            for lines in open(f"{self.path}" , "r"):
                if "\n" in lines:
                    lines = lines.replace("\n" , "")

                if len(lines) > 0:
                    Content.append(lines)
            self.content = list(Content)

    def Check_File(self) -> bool:
        File_content = list(self.content)

        use = None
        specifics = None
        output_name = "output"
        lang = None
        desc = None

        for lines in File_content:
            if "use" in lines:
                use = True
            if "specific" in lines:
                specifics = True
            if "output-name" in lines:
                output_name = True
            if "lang" in lines:
                lang = True
            if "description" in lines:
                desc = True

        
        if use == None:
            print(f"Error : No `use` method specified in file {self.path} >> Program terminated!")
            sys.exit()

        if specifics == None:
            print("Error in `specifics {` - `}` in file {filename} >> Program Terminated!".replace("{filename}" , self.path))
            sys.exit()
        
        if output_name == "output":
            print("No output name given (without extension) >> Using Default - `output`.")

        if lang == None:
            print("No programming language  specified.")
        
        if desc == None:
            print(f"Error : No `description` parameter was specified >> Program Terminated!")
            sys.exit()

        return True

    def make(self):
        self.Check_File()

        for lines in self.content:
            lines = str(lines)
            if "use" in lines:
                use_method = lines.split("use")[1]
                print(use_method)

            if "lang" in lines and "code" in use_method:
                lang = lines.split("=>")[1]
                print(lang)

            if "description" in lines:
                values = []
                is_here = False
                for description in self.content:
                    description = str(description)
                    if "description" in description:
                        is_here = True
                    
                    if "description" in description:
                        description = description.replace("description " , "")
                        description = description.replace("=>" , "")

                    if is_here == True:
                        if ";" in description:
                            values.append(description.replace(";", ""))
                        else:
                            values.append(description)
                    
                    if ";" in description:
                        break

                string_value = ""
                for vals in values:
                    string_value += str(vals) + " "
        
        if "code" in use_method:
            Prompt_string = f"make a {use_method} in programming language {lang} that satisfy these requirements\n{string_value}"
        else:
            prompt_string = f"{string_value}"
        print(Prompt_string)
                


Work("/workspaces/ALFRED/test2.line").make()
