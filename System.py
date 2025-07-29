import os, sys
# from llama_cpp import Llama

# MODEL_PATH = "FILES\\model\\deepseek-coder-1.3b-instruct.Q8_0.gguf"

# LLM = Llama( model_path=MODEL_PATH, n_ctx=6144, n_threads=10, verbose=False )


# def Responce(text:str) -> str:

#     out = LLM(text, max_tokens=100, stop=["User:", "Butler:"], echo=False)
#     answer = out["choices"][0]["text"].strip()

#     return answer

# print(Responce("Make a hello world code in java"))

input_Filename:str = None
function_to_perform:str = "create"

if sys.argv:
    Command:list = list(sys.argv)


    if "create" in Command:
        function_to_perform:str = "create"
        if "-f" in Command:
            input_Filename:str =  Command[(int(Command.index("-f")) + 1)]

            if "\\" not in input_Filename:
                input_Filename:str = f"{os.getcwd()}\\{input_Filename}"


        
if input_Filename != None:
    print(function_to_perform, input_Filename)

    