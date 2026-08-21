import threading
import logging
import queue
import time
import sounddevice as sd
import numpy as np

# Note: Ensure torch 2.5+ is installed in the environment
import torch
from pocket_tts import TTSModel

import re
from concurrent.futures import ThreadPoolExecutor
from FILES.LATENCY_RECORDER import track_latency

logger = logging.getLogger(__name__)

@track_latency("alfred_voice.chunk_text")
def chunk_text(text: str, max_words: int = 30) -> list[str]:
    """
    Splits text into chunks of maximum max_words. If a chunk does not end
    with punctuation, looks ahead up to 8 words to find a punctuation mark
    and complete the sentence/clause.
    """
    words = text.strip().split()
    if not words:
        return []
        
    chunks = []
    i = 0
    n = len(words)
    
    def ends_with_punctuation(word: str) -> bool:
        if not word:
            return False
        return word[-1] in ".!?,;:"
        
    while i < n:
        if n - i <= max_words:
            chunks.append(" ".join(words[i:]))
            break
            
        # Check if the word at the limit ends with punctuation
        limit_idx = i + max_words - 1
        if ends_with_punctuation(words[limit_idx]):
            chunks.append(" ".join(words[i : i + max_words]))
            i += max_words
        else:
            # Look ahead up to 8 words for punctuation
            found_idx = -1
            for j in range(i + max_words, min(i + max_words + 8, n)):
                if ends_with_punctuation(words[j]):
                    found_idx = j
                    break
            
            if found_idx != -1:
                chunks.append(" ".join(words[i : found_idx + 1]))
                i = found_idx + 1
            else:
                chunks.append(" ".join(words[i : i + max_words]))
                i += max_words
                
    return chunks

class AlfredVoiceModule:
    """
    Production-grade integration of Kyutai's Pocket TTS for the ALFRED ecosystem.
    Runs on CPU, chunks text, generates chunks simultaneously via ThreadPool, 
    and plays them sequentially.
    """
    def __init__(self, voice_name: str = "peter_yearsley", sample_rate: int = 24000):
        self.voice_name = voice_name
        self.sample_rate = sample_rate
        self.model = None
        self.voice_state = None
        
        # Unbounded queue for raw chunks to keep speak() non-blocking
        self.generation_queue = queue.Queue()
        
        # Bounded queue for handling sequential audio playback (max 8 chunks ahead)
        self.playback_queue = queue.Queue(maxsize=8)
        self.is_initialized = False
        self._shutdown_flag = threading.Event()
        
        # Executor for simultaneous chunk generation
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Start initialization
        self._initialize()
        
        # Start the background threads
        if self.is_initialized:
            self._generation_thread = threading.Thread(target=self._process_generation_queue, daemon=True, name="AlfredGenerationWorker")
            self._generation_thread.start()
            
            self._playback_thread = threading.Thread(target=self._process_playback_queue, daemon=True, name="AlfredPlaybackWorker")
            self._playback_thread.start()

    def _initialize(self):
        """Pre-loads the 100M parameter model and voice state into memory."""
        try:
            logger.info("Initializing Pocket TTS on CPU...")
            self.model = TTSModel.load_model()
            
            logger.info(f"Loading voice state for: {self.voice_name}")
            self.voice_state = self.model.get_state_for_audio_prompt(self.voice_name)
            
            self.is_initialized = True
            logger.info("AlfredVoiceModule initialized successfully. Ready for audio playback.")
        except Exception as e:
            logger.error(f"Failed to initialize AlfredVoiceModule: {e}")
            self.is_initialized = False

    @track_latency("AlfredVoiceModule.speak")
    def speak(self, text: str) -> None:
        """
        Strictly typed speak method. Chunks the text, submits to executor for 
        simultaneous generation, and enqueues futures for sequential playback.
        """
        if not self.is_initialized:
            logger.error("Cannot speak: Voice module is not initialized.")
            return

        if not text or not text.strip():
            return

        chunks = chunk_text(text, max_words=30) # Reduced to 30 to guarantee staying under 50 tokens
        logger.debug(f"Split text into {len(chunks)} chunks. Queuing for generation.")
        
        # Queue chunks to be managed by the generation thread
        for chunk in chunks:
            if chunk.strip():
                self.generation_queue.put(chunk)

    def _process_generation_queue(self):
        """Worker loop that limits simultaneous generation to maxsize of playback_queue."""
        while not self._shutdown_flag.is_set():
            try:
                chunk = self.generation_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                # Submit chunk to thread pool
                future = self.executor.submit(self._generate_audio_tensor, chunk)
                
                # Push future to playback queue. 
                # If queue is full (8 items), this blocks until an item is spoken,
                # ensuring we only generate up to 8 chunks ahead!
                self.playback_queue.put(future)
            except Exception as e:
                logger.error(f"Error queuing chunk for generation: {e}")
            finally:
                self.generation_queue.task_done()

    @track_latency("AlfredVoiceModule._generate_audio_tensor")
    def _generate_audio_tensor(self, text: str):
        """Worker function that generates audio latents for a single chunk."""
        try:
            # Ensure text ends with punctuation so TTS doesn't drop the last word
            if text and not text[-1] in ".!?,;":
                text += "."
            audio_tensor = self.model.generate_audio(self.voice_state, text)
            
            if isinstance(audio_tensor, torch.Tensor):
                audio_array = audio_tensor.detach().cpu().numpy()
            else:
                audio_array = np.array(audio_tensor)
                
            if audio_array.ndim == 1:
                audio_array = audio_array.reshape(-1, 1)
                
            return audio_array
        except torch.cuda.OutOfMemoryError as e:
            logger.error(f"PyTorch Memory Error during audio generation: {e}")
        except Exception as e:
            logger.error(f"Error during audio generation: {e}")
        return None

    def _process_playback_queue(self):
        """Background worker loop that waits for chunks to finish generating and plays them sequentially."""
        while not self._shutdown_flag.is_set():
            try:
                future = self.playback_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                # This will block until the specific chunk finishes its simultaneous generation
                audio_array = future.result() 
                
                if audio_array is not None:
                    # Pad with 50ms silence at the start and 100ms at the end to prevent cutoffs
                    start_pad = np.zeros((int(self.sample_rate * 0.1), 1), dtype=audio_array.dtype)
                    end_pad = np.zeros((int(self.sample_rate * 0.15), 1), dtype=audio_array.dtype)
                    padded_audio = np.vstack((start_pad, audio_array, end_pad))
                    
                    logger.debug("Playing generated chunk via sounddevice...")
                    sd.play(padded_audio, samplerate=self.sample_rate)
                    sd.wait() 
            except sd.PortAudioError as e:
                 logger.error(f"Sounddevice/PortAudio Error (Is an audio device available?): {e}")
            except Exception as e:
                 logger.error(f"Error during audio playback: {e}")
            finally:
                self.playback_queue.task_done()

    def shutdown(self):
        """Gracefully shuts down the voice module worker thread."""
        logger.info("Shutting down AlfredVoiceModule...")
        self._shutdown_flag.set()
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        if hasattr(self, '_generation_thread') and self._generation_thread.is_alive():
            self._generation_thread.join(timeout=2.0)
        if hasattr(self, '_playback_thread') and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=2.0)
