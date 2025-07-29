import os, sys
# from llama_cpp import Llama

# MODEL_PATH = "FILES\\model\\deepseek-coder-1.3b-instruct.Q8_0.gguf"

# LLM = Llama( model_path=MODEL_PATH, n_ctx=6144, n_threads=10, verbose=False )


# def Responce(text:str) -> str:

#     out = LLM(text, max_tokens=100, stop=["User:", "Butler:"], echo=False)
#     answer = out["choices"][0]["text"].strip()

#     return answer

# print(Responce("Make a hello world code in java"))

output_Filename = "output.py"


if sys.argv:
    Command = list(sys.argv)
    
    Command = Command.pop(0) # Removies filename



    if "create" in Command:
        if "-f" in Command:
            input_Filename =  Command[(int(Command.index("-f")) + 1)]
        if "-o" in Command:
            output_Filename = Command[(int(Command.index("-o")) + 1)]    

            

        