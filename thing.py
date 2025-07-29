
from llama_cpp import Llama

MODEL_PATH = "FILES\model\Coder.gguf"

LLM = Llama( model_path=MODEL_PATH, n_ctx=6144, n_threads=10, verbose=False )

def write_output(filepath:str, contents:str):
    with open(f"{filepath}/output" , "r") as file:
        file.write(f"{contents}")
                       
def Responce(text:str) -> str:

    out = LLM(text, max_tokens=100, stop=["User:", "Butler:"], echo=False)
    answer = out["choices"][0]["text"].strip()

    return answer

response = Responce('''make a  code  in programming language  python that satisfy these requirements
     To make a simple basic algebric calculator example it should be able to find x in `x+3=5 > gives x=2`      and also like `3x+2 = 11 > gives x=3`      
                       ''')
write_output("/workspaces/ALFRED", response)

                       