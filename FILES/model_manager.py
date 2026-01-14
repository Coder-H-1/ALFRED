import gc, os 
from llama_cpp import Llama
from FILES.util_functions import speak
from FILES.intent import IntentTrainer
from FILES.commands import search_files
import random

#gc = garbage collector

MODELS = {
    "linux command" : "FILES\\model\\qwen-linux-q8_0.gguf",
    "quote" : "FILES\\model\\quotes_q8_0.gguf", 
    "linux tool" : "FILES\\model\\linux_tools_q8_0.gguf"
} # Model paths 


class ModelManager: ### Manages Chat and workflow models
    "Manages model"
    
    def __init__(self) -> None:
        self.model = None
        self.current_model_name = None
        self.filename:str = search_files(query="intents.jsonl",search_path="/workspace/ALFRED", is_commanded=True)

    def load_model(self, model_path:str, name:str, context_len: int) -> None:  ### Loads LLM model in self.model 
        "Loads model as object in (self.model)"

        if os.path.exists(model_path)!=True: 
            speak("You currently don't have model for specified function. I don't actually know what to do."); return
        
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
        self.current_model_name = str(name)

    def unload_model(self) -> None:  ### Unloads LLM model from self.model and runs garbage collector to free RAM 
        "Unloads and deletes (self.model) object and runs Garbage collector"

        print(f"[manager] Unloading model: {self.current_model_name}")
        del self.model      ### deletes self.model object 
        self.model = None
        self.current_model_name = None
        gc.collect()    ### runs garbage collector

    def prompt(self, prompt:str, max_token:int) -> str:  ### Runs and prompts the self.model > return string ( reply )  
        "Prompts the loaded (self.model) and returns string"

        if self.model:
            output = self.model(
                prompt,
                max_tokens=int(max_token),
                temperature=0.8,
                top_p=0.9,
                repeat_penalty=1.1,
            )
            return output["choices"][random.randint(0,1)]["text"].strip()
        else:
            print("No models loaded -> first load a model then do prompts.\n")
            return

    def Start_Intent_Trainer(self):
        trainer = IntentTrainer(
            base_model="distilbert-base-uncased",
            output_dir="FILES/model/alfred_intent_model"
        )

        trainer.train(
            train_file=self.filename,
            epochs=3,
            batch_size=8
        )
