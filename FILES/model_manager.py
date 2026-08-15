import gc
import os 
from llama_cpp import Llama
from FILES.util_functions import speak
from FILES.logger import get_logger

logger = get_logger(__name__)

# Base directory for absolute path resolution
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODELS = {
    "linux command" : os.path.join(_BASE_DIR, "FILES", "model", "qwen-linux-q8_0.gguf"),
    "quote" : os.path.join(_BASE_DIR, "FILES", "model", "quotes_q8_0.gguf"), 
    "linux tool" : os.path.join(_BASE_DIR, "FILES", "model", "linux_tools_q8_0.gguf")
}

class ModelManager:
    """Manages Chat and workflow models."""
    
    def __init__(self) -> None:
        self.model = None
        self.current_model_name = None
        self.filename = os.path.join(_BASE_DIR, "FILES", "intents.jsonl")

    def load_model(self, model_path:str, name:str, context_len: int) -> None:
        """Loads LLM model in self.model."""
        if not os.path.exists(model_path): 
            logger.warning(f"Requested model path does not exist: {model_path}")
            speak("You currently don't have model for specified function. I don't actually know what to do.")
            return
        
        if self.model is not None:
            self.unload_model()

        logger.info(f"Loading model: {name} from path: {model_path} (context: {context_len})")
        try:
            self.model = Llama(
                model_path=model_path,
                n_ctx=int(context_len),
                n_threads=8,
                n_batch=256,
                verbose=False,
            )
            self.current_model_name = str(name)
            logger.info(f"Successfully loaded model: {name}")
        except Exception as e:
            logger.error(f"Failed to load model {name}: {e}", exc_info=True)

    def unload_model(self) -> None:
        """Unloads LLM model from self.model and runs garbage collector to free RAM."""
        if self.model is not None:
            logger.info(f"Unloading model: {self.current_model_name}")
            del self.model
            self.model = None
            self.current_model_name = None
            gc.collect()
            logger.info("Garbage collection complete, model memory freed.")

    def prompt(self, prompt:str, max_token:int) -> str:
        """Runs and prompts the self.model > return string ( reply )."""
        if self.model:
            logger.debug(f"Prompting model '{self.current_model_name}' (max tokens: {max_token})")
            try:
                output = self.model(
                    prompt,
                    max_tokens=int(max_token),
                    temperature=0.8,
                    top_p=0.9,
                    repeat_penalty=1.1,
                )
                response = output["choices"][0]["text"].strip()
                logger.debug("Successfully generated response from model.")
                return response
            except Exception as e:
                logger.error(f"Error prompting model '{self.current_model_name}': {e}", exc_info=True)
                return ""
        else:
            logger.warning("No models loaded -> first load a model then do prompts.")
            return ""
