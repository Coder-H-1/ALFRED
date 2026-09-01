import os
import re
import zlib
import time
import struct
from datetime import datetime
from FILES.logger import get_logger

logger = get_logger(__name__)

MAGIC_HEADER = b"ALF1"  # 4 bytes magic signature
MIN_COMPRESS_SIZE = 1024  # 1 KB minimum size threshold

# Common tokens dictionary for pre-processing log text
COMMON_TOKENS = [
    "[INFO]", "[DEBUG]", "[WARNING]", "[ERROR]", "[CRITICAL]",
    "[alfred_voice]", "[root]", "[FILES.memory]", "[FILES.utils]",
    "[FILES.util_functions]", "[FILES.commands]", "[FILES.gui_controller]",
    "[FILES.plugin_host]", "[FILES.resource_monitor]", "[__main__]",
    "Initializing", "successfully", "Starting", "Failed to", "Received GUI command"
]

def _preprocess_text(text: str) -> bytes:
    """Replaces common tokens with short index markers to increase compression ratio."""
    for idx, token in enumerate(COMMON_TOKENS):
        # Replace token with non-printable marker character \x01\x00, \x01\x01, etc.
        marker = f"\x01{chr(idx)}"
        text = text.replace(token, marker)
    return text.encode('utf-8')

def _postprocess_bytes(data: bytes) -> str:
    """Restores common tokens from non-printable index markers."""
    text = data.decode('utf-8', errors='replace')
    for idx, token in enumerate(COMMON_TOKENS):
        marker = f"\x01{chr(idx)}"
        text = text.replace(marker, token)
    return text

def compress_log(log_path: str, output_path: str = None, force: bool = False) -> str:
    """Compresses a .log file into .compressed_logs format.
    
    Header structure (12 bytes):
    - Magic (4 bytes): b'ALF1'
    - CRC32 (4 bytes): unsigned int
    - Original Size (4 bytes): unsigned int
    Followed by zlib compressed payload.
    """
    if not os.path.exists(log_path):
        logger.warning(f"File not found for compression: {log_path}")
        return None

    orig_size = os.path.getsize(log_path)
    if not force and orig_size < MIN_COMPRESS_SIZE:
        logger.info(f"Skipping compression for {os.path.basename(log_path)} (Size {orig_size} B < {MIN_COMPRESS_SIZE} B threshold)")
        return None

    if output_path is None:
        output_path = log_path + ".compressed_logs"

    try:
        with open(log_path, 'rb') as f:
            raw_bytes = f.read()

        # Calculate CRC32 checksum on original data
        crc32_val = zlib.crc32(raw_bytes) & 0xffffffff

        # Preprocess text tokens then compress payload with zlib
        text_content = raw_bytes.decode('utf-8', errors='replace')
        preprocessed = _preprocess_text(text_content)
        compressed_payload = zlib.compress(preprocessed, level=9)

        # Pack header: 4B magic + 4B crc32 + 4B orig_size
        header = struct.pack(">4sII", MAGIC_HEADER, crc32_val, orig_size)

        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(compressed_payload)

        comp_size = os.path.getsize(output_path)
        savings = (1.0 - (comp_size / orig_size)) * 100.0 if orig_size > 0 else 0.0
        logger.info(f"Compressed {os.path.basename(log_path)}: {orig_size/1024:.2f}KB -> {comp_size/1024:.2f}KB ({savings:.1f}% savings)")

        # Delete original log file after successful compression
        os.remove(log_path)
        return output_path
    except Exception as e:
        logger.error(f"Failed to compress log file {log_path}: {e}", exc_info=True)
        return None

def read_compressed_log(compressed_path: str) -> str:
    """Reads and decompresses a .compressed_logs file into text in memory without modifying the file."""
    if not os.path.exists(compressed_path):
        logger.warning(f"Compressed file not found: {compressed_path}")
        return ""

    try:
        with open(compressed_path, 'rb') as f:
            header = f.read(12)
            if len(header) < 12:
                raise ValueError("Invalid compressed file header")
            
            magic, expected_crc32, expected_orig_size = struct.unpack(">4sII", header)
            if magic != MAGIC_HEADER:
                raise ValueError(f"Invalid magic signature: {magic}")

            compressed_payload = f.read()

        decompressed_preprocessed = zlib.decompress(compressed_payload)
        restored_text = _postprocess_bytes(decompressed_preprocessed)
        raw_bytes = restored_text.encode('utf-8')

        # CRC32 Checksum verification
        actual_crc32 = zlib.crc32(raw_bytes) & 0xffffffff
        if actual_crc32 != expected_crc32:
            raise ValueError(f"CRC32 Checksum Mismatch! File corrupt. Expected {hex(expected_crc32)}, got {hex(actual_crc32)}")

        return restored_text
    except Exception as e:
        logger.error(f"Failed to read compressed log file {compressed_path}: {e}", exc_info=True)
        return ""

def decompress_log(compressed_path: str, output_path: str = None, remove_compressed: bool = True) -> str:
    """Decompresses a .compressed_logs file back to original .log file format."""
    if not os.path.exists(compressed_path):
        logger.warning(f"Compressed file not found: {compressed_path}")
        return None

    if output_path is None:
        if compressed_path.endswith(".compressed_logs"):
            output_path = compressed_path[:-16]
        else:
            output_path = compressed_path + ".log"

    try:
        restored_text = read_compressed_log(compressed_path)
        if not restored_text and os.path.getsize(compressed_path) > 12:
            return None

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(restored_text)

        logger.info(f"Decompressed {os.path.basename(compressed_path)} -> {os.path.basename(output_path)} (CRC32 Verified)")
        
        # Remove compressed file after successful decompression if requested
        if remove_compressed:
            os.remove(compressed_path)
        return output_path
    except Exception as e:
        logger.error(f"Failed to decompress log file {compressed_path}: {e}", exc_info=True)
        return None

def cleanup_old_logs(logs_dir: str = None, retention_days: int = 15):
    """Deletes .compressed_logs files older than retention_days (default 15 days)."""
    if logs_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(base_dir, "logs")

    if not os.path.exists(logs_dir):
        return

    now = time.time()
    cutoff = now - (retention_days * 86400)

    for item in os.listdir(logs_dir):
        if item.endswith(".compressed_logs"):
            file_path = os.path.join(logs_dir, item)
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted old compressed log (>15 days old): {item}")
                except Exception as e:
                    logger.error(f"Failed to delete old log {item}: {e}")

def compress_all_rotated_logs(logs_dir: str = None):
    """Compresses all rotated daily log files (e.g. alfred.log.2026-08-15) in logs directory."""
    if logs_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(base_dir, "logs")

    if not os.path.exists(logs_dir):
        return

    # First cleanup compressed logs older than 15 days
    cleanup_old_logs(logs_dir, retention_days=15)

    for item in os.listdir(logs_dir):
        # Match rotated log format (alfred.log.YYYY-MM-DD or similar, excluding active alfred.log and .compressed_logs)
        if item.startswith("alfred.log.") and not item.endswith(".compressed_logs"):
            full_path = os.path.join(logs_dir, item)
            if os.path.isfile(full_path):
                compress_log(full_path)
