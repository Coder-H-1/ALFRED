import gc, os 
from llama_cpp import Llama
from util_functions import speak

MODELS = {
    "linux command" : "FILES\\model\\qwen-linux-q8_0.gguf",
    "quote" : "FILES\\model\\quotes_q8_0.gguf", 
    "linux tool" : "FILES\\model\\linux_tools_q8_0.gguf"
} 


class ModelManager:
    def __init__(self) -> None:
        self.model = None
        self.current_model_name = None

    def load_model(self, model_path:str, name:str, context_len: int) -> None:
        if os.path.exists(model_path)!=True: speak("You currently don't have model for specified function. ")
        if self.model is not None:
            self.unload_model()

        print(f"[manager] Loading model: {name}")
        self.model = Llama(
            model_path=model_path,
            n_ctx=int(context_len),
            n_threads=8,
            n_batch=256,
            verbose=False,
        )
        self.current_model_name = name

    def unload_model(self) -> None:
        print(f"[manager] Unloading model: {self.current_model_name}")
        del self.model
        self.model = None
        self.current_model_name = None
        gc.collect()

    def prompt(self, prompt:str, max_token:int) -> str:
        output = self.model(
            prompt,
            max_tokens=int(max_token),
            temperature=0.8,
            top_p=0.9,
            repeat_penalty=1.1,
        )
        return output["choices"][0]["text"].strip()



