"""
log_compressor.py — Compression, archiving, and retrieval utility for ALFRED logs.

Features:
- Compresses rotated daily logs using custom binary format (.compressed_logs) with CRC32 verification.
- Batch Zip Archiver:
    - Automatically bundles files older than 5 days in groups of 5 into single zip archives formatted as:
      from_DD_MM_YYYY_to_DD_MM_YYYY_alfred_log.zip (or from_DD_MM_YYYY_to_DD_MM_YYYY_alfred_latency_log.zip).
- Retrieval by function via CLI:
    - Filter logs by function/module keyword.
    - If --output <filepath> is specified, writes all matching records to file (creating path if missing).
    - If not specified, displays the last 50 matching lines in terminal.
- Default view: Shows the last 50 lines of the latest active log file.
- Cleanup: Deletes standalone compressed log records older than 5 days (--clean).
"""

import os
import re
import sys
import zlib
import time
import struct
import zipfile
import argparse
from datetime import datetime, timedelta
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from FILES.logger import get_logger

logger = get_logger(__name__)

MAGIC_HEADER = b"ALF1"  # 4 bytes magic signature
MIN_COMPRESS_SIZE = 1024  # 1 KB minimum size threshold

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOGS_DIR = os.path.join(_BASE_DIR, "logs")

# Common tokens dictionary for pre-processing log text
COMMON_TOKENS = [
    "[INFO]", "[DEBUG]", "[WARNING]", "[ERROR]", "[CRITICAL]",
    "[alfred_voice]", "[root]", "[FILES.memory]", "[FILES.utils]",
    "[FILES.util_functions]", "[FILES.commands]",
    "[FILES.plugin_host]", "[MCP.bridge]", "[__main__]",
    "Initializing", "successfully", "Starting", "Failed to"
]


def _preprocess_text(text: str) -> bytes:
    """Replaces common tokens with short index markers to increase compression ratio."""
    for idx, token in enumerate(COMMON_TOKENS):
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
    """Compresses a .log file into .compressed_logs format."""
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

        crc32_val = zlib.crc32(raw_bytes) & 0xffffffff
        text_content = raw_bytes.decode('utf-8', errors='replace')
        preprocessed = _preprocess_text(text_content)
        compressed_payload = zlib.compress(preprocessed, level=9)

        header = struct.pack(">4sII", MAGIC_HEADER, crc32_val, orig_size)
        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(compressed_payload)

        comp_size = os.path.getsize(output_path)
        savings = (1.0 - (comp_size / orig_size)) * 100.0 if orig_size > 0 else 0.0
        logger.info(f"Compressed {os.path.basename(log_path)}: {orig_size/1024:.2f}KB -> {comp_size/1024:.2f}KB ({savings:.1f}% savings)")

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

        actual_crc32 = zlib.crc32(raw_bytes) & 0xffffffff
        if actual_crc32 != expected_crc32:
            raise ValueError(f"CRC32 Checksum Mismatch! Expected {hex(expected_crc32)}, got {hex(actual_crc32)}")

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
        if remove_compressed:
            os.remove(compressed_path)
        return output_path
    except Exception as e:
        logger.error(f"Failed to decompress log file {compressed_path}: {e}", exc_info=True)
        return None


# ── Batch Zip Archiver (>5 Days Old in Groups of 5) ───────────────────────────

def archive_old_logs(logs_dir: str = None, min_age_days: int = 5, batch_size: int = 5) -> list[str]:
    """
    Bundles compressed logs older than min_age_days in groups of batch_size (5)
    into a single zip file formatted:
      from_DD_MM_YYYY_to_DD_MM_YYYY_alfred_log.zip
    Removes the source compressed logs upon successful packaging.
    """
    if logs_dir is None:
        logs_dir = DEFAULT_LOGS_DIR

    if not os.path.exists(logs_dir):
        return []

    cutoff_date = datetime.now() - timedelta(days=min_age_days)
    eligible_files = []

    for item in os.listdir(logs_dir):
        if not item.endswith(".compressed_logs"):
            continue

        # Extract date string: alfred.log.YYYY-MM-DD.compressed_logs or YYYY-MM-DD.log.compressed_logs
        match = re.search(r'(\d{4}-\d{2}-\d{2})', item)
        if not match:
            continue

        try:
            file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
            if file_date < cutoff_date:
                full_path = os.path.join(logs_dir, item)
                eligible_files.append({"date": file_date, "path": full_path, "name": item})
        except ValueError:
            continue

    # Sort chronologically
    eligible_files.sort(key=lambda x: x["date"])

    created_zips = []
    while len(eligible_files) >= batch_size:
        batch = eligible_files[:batch_size]
        eligible_files = eligible_files[batch_size:]

        start_str = batch[0]["date"].strftime("%d_%m_%Y")
        end_str = batch[-1]["date"].strftime("%d_%m_%Y")
        zip_name = f"from_{start_str}_to_{end_str}_alfred_log.zip"
        zip_path = os.path.join(logs_dir, zip_name)

        try:
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for f_info in batch:
                    zf.write(f_info["path"], arcname=f_info["name"])

            for f_info in batch:
                try:
                    if os.path.exists(f_info["path"]):
                        os.remove(f_info["path"])
                except Exception:
                    pass

            logger.info(f"Created batch log zip archive: {zip_name} ({len(batch)} files)")
            created_zips.append(zip_name)
        except Exception as e:
            logger.error(f"Failed to create batch zip archive {zip_name}: {e}")

    return created_zips


def cleanup_old_logs(logs_dir: str = None, retention_days: int = 5):
    """
    Cleans up old logs:
    1. First packages >=5 old files into batch zip archives.
    2. Deletes any remaining standalone .compressed_logs older than retention_days (default 5 days).
    """
    if logs_dir is None:
        logs_dir = DEFAULT_LOGS_DIR

    if not os.path.exists(logs_dir):
        return 0

    # First attempt batch zip archiving in groups of 5
    archive_old_logs(logs_dir, min_age_days=retention_days, batch_size=5)

    cutoff = time.time() - (retention_days * 86400)
    deleted_count = 0

    for item in os.listdir(logs_dir):
        if item.endswith(".compressed_logs"):
            file_path = os.path.join(logs_dir, item)
            try:
                if os.path.getmtime(file_path) < cutoff:
                    os.remove(file_path)
                    logger.info(f"Deleted old compressed log (>5 days old): {item}")
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete old log {item}: {e}")

    return deleted_count


def compress_all_rotated_logs(logs_dir: str = None):
    """Compresses all rotated daily log files in logs directory and executes batch archiving."""
    if logs_dir is None:
        logs_dir = DEFAULT_LOGS_DIR

    if not os.path.exists(logs_dir):
        return

    # First trigger batch archiving & 5-day cleanup
    cleanup_old_logs(logs_dir, retention_days=5)

    for item in os.listdir(logs_dir):
        if item.startswith("alfred.log.") and not item.endswith(".compressed_logs") and not item.endswith(".zip"):
            full_path = os.path.join(logs_dir, item)
            if os.path.isfile(full_path):
                compress_log(full_path)


# ── Function-Based Retrieval & CLI ────────────────────────────────────────────

def get_all_log_sources(logs_dir: str = None) -> list[dict]:
    """Returns all log files (active .log and .compressed_logs) sorted chronologically."""
    if logs_dir is None:
        logs_dir = DEFAULT_LOGS_DIR

    sources = []
    if not os.path.exists(logs_dir):
        return sources

    for item in os.listdir(logs_dir):
        full_path = os.path.join(logs_dir, item)
        if item == "alfred.log":
            sources.append({"name": item, "path": full_path, "type": "active", "mtime": os.path.getmtime(full_path)})
        elif item.startswith("alfred.log.") and item.endswith(".compressed_logs"):
            sources.append({"name": item, "path": full_path, "type": "compressed", "mtime": os.path.getmtime(full_path)})
        elif item.endswith(".zip") and item.startswith("from_"):
            sources.append({"name": item, "path": full_path, "type": "zip", "mtime": os.path.getmtime(full_path)})

    sources.sort(key=lambda s: s["mtime"])
    return sources


def read_lines_from_source(source: dict) -> list[str]:
    """Reads lines from an active file, compressed file, or zip archive."""
    path = source["path"]
    t = source["type"]

    if t == "active":
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return [line.rstrip("\r\n") for line in f if line.strip()]
        except Exception:
            return []

    elif t == "compressed":
        content = read_compressed_log(path)
        return [line.rstrip("\r\n") for line in content.splitlines() if line.strip()] if content else []

    elif t == "zip":
        lines = []
        try:
            with zipfile.ZipFile(path, "r") as zf:
                for name in zf.namelist():
                    data = zf.read(name)
                    # Data is compressed payload
                    decompressed = _read_bytes_payload(data)
                    if decompressed:
                        lines.extend([l.rstrip("\r\n") for l in decompressed.splitlines() if l.strip()])
        except Exception:
            pass
        return lines

    return []


def _read_bytes_payload(payload_bytes: bytes) -> str:
    """Helper to read raw .compressed_logs payload from memory."""
    if len(payload_bytes) < 12:
        return ""
    try:
        header = payload_bytes[:12]
        magic, expected_crc32, _ = struct.unpack(">4sII", header)
        if magic != MAGIC_HEADER:
            return ""
        decompressed_pre = zlib.decompress(payload_bytes[12:])
        restored = _postprocess_bytes(decompressed_pre)
        return restored
    except Exception:
        return ""


def retrieve_function_logs(function_name: str, output_path: str = None, limit_terminal: int = 50) -> list[str]:
    """
    Retrieves all log records matching function_name across active and archived logs.
    If output_path is provided, writes all matches to file (creates dirs).
    If output_path is None, displays the last limit_terminal lines in the terminal.
    """
    sources = get_all_log_sources()
    matched_lines = []
    fn_lower = function_name.lower().strip()

    for s in sources:
        lines = read_lines_from_source(s)
        for l in lines:
            if fn_lower in l.lower():
                matched_lines.append(l)

    if output_path:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for line in matched_lines:
                f.write(line + "\n")

        print(f"\n  Exported {len(matched_lines)} log records matching '{function_name}' to:\n  -> {output_path}\n")
    else:
        # Show in terminal (last 50 lines)
        print(f"\n╔════════════════════════════════════════════════════════════════════════════════════╗")
        print(f"║ LOG RETRIEVAL FOR FUNCTION: {function_name:<54} ║")
        print(f"╠════════════════════════════════════════════════════════════════════════════════════╣")

        if not matched_lines:
            print(f"║  No log entries found matching '{function_name}'.{' ' * max(0, 48 - len(function_name))}║")
            print(f"╚════════════════════════════════════════════════════════════════════════════════════╝\n")
            return []

        displayed = matched_lines[-limit_terminal:]
        print(f"║  Showing last {len(displayed)} of {len(matched_lines)} total matching entries:{' ' * 32}║")
        print(f"╟────────────────────────────────────────────────────────────────────────────────────╢")
        for line in displayed:
            print(f"  {line}")
        print(f"╚════════════════════════════════════════════════════════════════════════════════════╝\n")

    return matched_lines


def show_latest_logs(lines_count: int = 50):
    """Displays the last lines_count lines of the latest active log file."""
    active_log = os.path.join(DEFAULT_LOGS_DIR, "alfred.log")
    if not os.path.exists(active_log):
        print("\n  [!] No active alfred.log found.\n")
        return

    try:
        with open(active_log, "r", encoding="utf-8", errors="replace") as f:
            all_lines = [line.rstrip("\r\n") for line in f if line.strip()]

        displayed = all_lines[-lines_count:]
        print(f"\n╔════════════════════════════════════════════════════════════════════════════════════╗")
        print(f"║ ALFRED LATEST LOGS (Last {len(displayed)} lines of alfred.log){' ' * 37}║")
        print(f"╠════════════════════════════════════════════════════════════════════════════════════╣")
        for line in displayed:
            print(f"  {line}")
        print(f"╚════════════════════════════════════════════════════════════════════════════════════╝\n")
    except Exception as e:
        print(f"\n  [!] Error reading active log: {e}\n")


def _cli_help():
    print("""
ALFRED LOG COMPRESSOR & RETRIEVER CLI
Usage: python .\\FILES\\log_compressor.py [options]

Options:
  --function <name>     Retrieve logs matching the specified function or module
  --output <filepath>   Export all matched logs to specified filepath (creates folders)
  --archive             Bundle logs older than 5 days into groups of 5 zip archives
  --clean               Clean/delete standalone compressed logs older than 5 days
  --lines <N>           Number of terminal lines to display (default: 50)
  --help, -h            Show this help message

Default behavior:
  Running without arguments displays the last 50 lines of the latest active alfred.log.
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--function", "--fn", type=str, default=None, dest="function", help="Function name to filter")
    parser.add_argument("--output", "-o", type=str, default=None, help="Export output file path")
    parser.add_argument("--lines", "-n", type=int, default=50, help="Terminal lines limit")
    parser.add_argument("--archive", action="store_true", help="Batch zip files older than 5 days in groups of 5")
    parser.add_argument("--clean", action="store_true", help="Clean records older than 5 days")
    parser.add_argument("--help", "-h", action="store_true", help="Show help")

    args, _ = parser.parse_known_args()

    if args.help:
        _cli_help()
    elif args.archive:
        created = archive_old_logs(min_age_days=5, batch_size=5)
        if created:
            print(f"\n  Created {len(created)} batch zip archive(s):")
            for z in created:
                print(f"    - {z}")
            print()
        else:
            print("\n  No eligible files found to archive (requires >=5 files older than 5 days).\n")
    elif args.clean:
        del_count = cleanup_old_logs(retention_days=5)
        print(f"\n  Cleaned up {del_count} old standalone log files (>5 days old).\n")
    elif args.function:
        retrieve_function_logs(function_name=args.function, output_path=args.output, limit_terminal=args.lines)
    else:
        # Default fallback: show last 50 lines of latest log
        show_latest_logs(lines_count=args.lines)
