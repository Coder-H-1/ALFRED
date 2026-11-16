import os
import re
import logging
from logging.handlers import TimedRotatingFileHandler

_initialized = False

# Patterns for sensitive data redaction
REDACTION_PATTERNS = [
    re.compile(r'(sk-[a-zA-Z0-9_\-]{16,})', re.IGNORECASE),
    re.compile(r'(hf_[a-zA-Z0-9]{20,})', re.IGNORECASE),
    re.compile(r'(Bearer\s+)[a-zA-Z0-9_\-\.]{16,}', re.IGNORECASE),
    re.compile(r'((?:api[_-]?key|secret|password|passwd|access[_-]?token|auth[_-]?token)\s*[:=]\s*["\']?)([^"\'\s,;]{6,})', re.IGNORECASE),
]

class RedactingFormatter(logging.Formatter):
    """Logging formatter that redacts API keys, tokens, and credentials."""

    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        redacted = orig
        for pat in REDACTION_PATTERNS:
            if "Bearer" in pat.pattern:
                redacted = pat.sub(r'\1[REDACTED_TOKEN]', redacted)
            elif "api" in pat.pattern:
                redacted = pat.sub(r'\1[REDACTED_SECRET]', redacted)
            else:
                redacted = pat.sub(r'[REDACTED]', redacted)
        return redacted

def setup_logging():
    global _initialized
    if _initialized:
        return
    
    # Create logs directory in project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    log_file = os.path.join(logs_dir, "alfred.log")
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Redacting Formatter
    formatter = RedactingFormatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # File handler (timed rotating daily, keep 7 days)
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=7, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Silence noisy third-party libraries
    logging.getLogger("pocket_tts").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    
    _initialized = True

def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
