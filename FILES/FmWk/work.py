import os,sys

class Work:
    def __init__(self, filepath:str):
        self.content = []
        self.path = str(filepath)
        self.filepath = os.path.split(filepath)[0]
        self.output_name = ""
        self.readFile()
        
        self.prompt = ""

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

    def make_thread(self) -> None:
        with open(f"{self.filepath}/{self.output_name}.py", "w") as FILE:
            FILE.write("""
from llama_cpp import Llama

MODEL_PATH = "FILES\\model\\Coder.gguf"

LLM = Llama( model_path=MODEL_PATH, n_ctx=6144, n_threads=10, verbose=False )

def write_output(filepath:str, contents:str):
    with open(f"{filepath}/output" , "r") as file:
        file.write(f"{contents}")
                       
def Responce(text:str) -> str:

    out = LLM(text, max_tokens=100, stop=["User:", "Butler:"], echo=False)
    answer = out["choices"][0]["text"].strip()

    return answer

response = Responce('''{prompt}
                       ''')
write_output("-filepath-", response)

                       """.replace("-filepath-" , self.filepath).replace("{prompt}", self.prompt))
            

    def make(self):
        self.Check_File()

        for lines in self.content:
            lines = str(lines)
            if "use" in lines:
                use_method = lines.split("use")[1]

            if "output-name" in lines:
                self.output_name = (str(lines.split("=>")[1]).replace(" ", ""))
            
            if "lang" in lines and "code" in use_method:
                lang = lines.split("=>")[1]
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
            Prompt_string = f"{string_value}"
        self.prompt = Prompt_string
        
        self.make_thread()


Work("/workspaces/ALFRED/test2.line").make()
'''
print
'''