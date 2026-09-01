"""
LATENCY_RECORDER.py — Performance latency tracker for ALFRED.

Records per-call latency data into thread-safe daily log files (logs/latency/YYYY-MM-DD.log).
On program exit:
    - Organizes latency records grouped by function name
    - Appends summary metrics per function (<function-name>, <average-query-length>, <average-time-taken-seconds>)
    - Compresses the organized log file using ALFRED's log compression mechanism (.compressed_logs)

Provides:
    - LatencyRecorder singleton class with thread-safe recording
    - @track_latency decorator for auto-instrumentation
    - CLI interface: --show <date>, --lines <number>, --function-name <name>, --list, --clean

Usage (standalone):
    python .\\FILES\\LATENCY_RECORDER.py --show 2026-09-01
    python .\\FILES\\LATENCY_RECORDER.py --show 2026-09-01 --lines 20
    python .\\FILES\\LATENCY_RECORDER.py --show 2026-09-01 --function-name commands.process_command
    python .\\FILES\\LATENCY_RECORDER.py --list
    python .\\FILES\\LATENCY_RECORDER.py --clean
"""

import os
import sys
import time
import atexit
import threading
import functools
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

# ─── Path & Imports ───────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATENCY_DIR = os.path.join(_BASE_DIR, "logs", "latency")
RETENTION_DAYS = 15

# Ensure parent directory is in path for imports
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from FILES.log_compressor import compress_log, decompress_log, read_compressed_log


# ─── LatencyRecorder ─────────────────────────────────────────────────────────

class LatencyRecorder:
    """Thread-safe file-based latency recorder with automatic exit reorganization and compression."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton — only one recorder per process."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._file_lock = threading.Lock()
        os.makedirs(LATENCY_DIR, exist_ok=True)
        
        # Register automatic reorganization & compression on program exit
        atexit.register(self.organize_and_compress_all)
        self._initialized = True

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_log_path(self, date_str: str = None) -> str:
        """Get active uncompressed log path for a specific date (default today)."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(LATENCY_DIR, f"{date_str}.log")

    def _get_compressed_path(self, date_str: str = None) -> str:
        """Get compressed log path for a specific date (default today)."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(LATENCY_DIR, f"{date_str}.log.compressed_logs")

    # ── Core Recording ────────────────────────────────────────────────────

    def record(self, source: str, query_length: int,
               query_received_at: float, output_at: float):
        """Write one thread-safe latency record to the daily log file."""
        duration = max(0.0, output_at - query_received_at)
        
        # Format timestamps
        req_dt = datetime.fromtimestamp(query_received_at).strftime("%Y-%m-%d %H:%M:%S.%f")[:-1]
        out_dt = datetime.fromtimestamp(output_at).strftime("%Y-%m-%d %H:%M:%S.%f")[:-1]
        
        # Record format: <filename.function-name>, <query length>, <query-received-at>, <time-of-output>, <duration float with 5 decimals>s
        line = f"{source}, {query_length}, {req_dt}, {out_dt}, {duration:.5f}s\n"
        
        log_path = self._get_log_path()
        with self._file_lock:
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
            except Exception:
                pass

    def startup_record(self):
        """Write a sentinel record marking program startup."""
        now = time.time()
        self.record(
            source="SYSTEM.STARTUP",
            query_length=0,
            query_received_at=now,
            output_at=now
        )

    # ── Exit Reorganization & Compression ─────────────────────────────────

    def organize_and_compress(self, log_path: str):
        """Organizes a single log file by function name, appends summaries, and compresses it."""
        if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
            return

        with self._file_lock:
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    raw_lines = f.readlines()

                # Group entries by function name while preserving entry records
                grouped_records = defaultdict(list)
                for line in raw_lines:
                    line_str = line.strip()
                    if not line_str or line_str.startswith("SUMMARY:"):
                        continue
                    
                    parts = [p.strip() for p in line_str.split(",")]
                    if len(parts) >= 5:
                        func_name = parts[0]
                        try:
                            q_len = int(parts[1])
                        except ValueError:
                            q_len = 0
                        
                        dur_str = parts[4].rstrip("s")
                        try:
                            duration = float(dur_str)
                        except ValueError:
                            duration = 0.0

                        grouped_records[func_name].append({
                            "line": line_str,
                            "query_length": q_len,
                            "duration": duration
                        })
                    else:
                        # Non-conforming lines kept under miscellaneous
                        grouped_records["OTHER"].append({
                            "line": line_str,
                            "query_length": 0,
                            "duration": 0.0
                        })

                if not grouped_records:
                    return

                # Write reorganized file with summary lines
                with open(log_path, "w", encoding="utf-8") as f:
                    for func_name in sorted(grouped_records.keys()):
                        items = grouped_records[func_name]
                        for item in items:
                            f.write(item["line"] + "\n")
                        
                        # Calculate summaries
                        total_items = len(items)
                        avg_qlen = sum(it["query_length"] for it in items) / total_items if total_items > 0 else 0.0
                        avg_dur = sum(it["duration"] for it in items) / total_items if total_items > 0 else 0.0
                        
                        # Summary line: SUMMARY: <function-name>, <average-query-length>, <average-time-taken-seconds>
                        summary_line = f"SUMMARY: {func_name}, {avg_qlen:.2f}, {avg_dur:.5f}s\n"
                        f.write(summary_line)
                        f.write("\n")  # Section spacing

                # Compress using ALFRED's native log compressor
                compress_log(log_path, force=True)
            except Exception as e:
                pass

    def organize_and_compress_all(self):
        """Scans latency directory for all uncompressed .log files and compresses them."""
        if not os.path.exists(LATENCY_DIR):
            return
        
        try:
            for item in os.listdir(LATENCY_DIR):
                if item.endswith(".log"):
                    full_path = os.path.join(LATENCY_DIR, item)
                    if os.path.isfile(full_path):
                        self.organize_and_compress(full_path)
        except Exception:
            pass

    # ── Cleanup ───────────────────────────────────────────────────────────

    def cleanup_old(self, days: int = RETENTION_DAYS) -> int:
        """Deletes latency files older than `days`. Returns count deleted."""
        if not os.path.exists(LATENCY_DIR):
            return 0

        cutoff = time.time() - (days * 86400)
        deleted = 0

        with self._file_lock:
            for item in os.listdir(LATENCY_DIR):
                if item.endswith(".log") or item.endswith(".compressed_logs"):
                    full_path = os.path.join(LATENCY_DIR, item)
                    try:
                        if os.path.getmtime(full_path) < cutoff:
                            os.remove(full_path)
                            deleted += 1
                    except Exception:
                        pass
        return deleted

    # ── Reading & Querying ────────────────────────────────────────────────

    def read_records(self, date_str: str) -> list[str]:
        """Read and return all lines for a given date, decompressing if necessary without modifying disk."""
        log_path = self._get_log_path(date_str)
        comp_path = self._get_compressed_path(date_str)

        # If uncompressed active log exists, read it
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                return [line.rstrip("\r\n") for line in f if line.strip()]

        # If compressed archive exists, decompress in memory
        if os.path.exists(comp_path):
            decompressed = read_compressed_log(comp_path)
            if decompressed:
                return [line.rstrip("\r\n") for line in decompressed.splitlines() if line.strip()]

        return []

    def get_available_dates(self) -> list[dict]:
        """Returns metadata for all available recorded dates."""
        if not os.path.exists(LATENCY_DIR):
            return []

        date_files = {}
        for item in os.listdir(LATENCY_DIR):
            if item.endswith(".log"):
                d = item[:-4]
                full = os.path.join(LATENCY_DIR, item)
                date_files[d] = {
                    "date": d,
                    "status": "Active (Uncompressed)",
                    "size_bytes": os.path.getsize(full),
                    "path": full
                }
            elif item.endswith(".log.compressed_logs"):
                d = item[:-20]
                full = os.path.join(LATENCY_DIR, item)
                if d not in date_files:
                    date_files[d] = {
                        "date": d,
                        "status": "Archived (Compressed)",
                        "size_bytes": os.path.getsize(full),
                        "path": full
                    }

        return sorted(date_files.values(), key=lambda x: x["date"], reverse=True)


# ─── Decorator ────────────────────────────────────────────────────────────────

def track_latency(source: str = None):
    """Decorator that auto-records latency for the wrapped function.

    Usage:
        @track_latency("commands.process_command")
        def process_command(command):
            ...

    The first string argument to the wrapped function is used as query_length.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Determine query length from first string arg
            q_len = 0
            for a in args:
                if isinstance(a, str):
                    q_len = len(a)
                    break

            label = source or f"{func.__module__}.{func.__qualname__}"
            q_start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                q_end = time.time()
                try:
                    recorder = LatencyRecorder()
                    recorder.record(
                        source=label,
                        query_length=q_len,
                        query_received_at=q_start,
                        output_at=q_end
                    )
                except Exception:
                    pass  # never break the decorated function
        return wrapper
    return decorator


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _cli_show(date_str: str, lines_limit: int = 50, function_filter: str = None):
    """--show <date> [--lines <N>] [--function-name <name>]"""
    recorder = LatencyRecorder()
    lines = recorder.read_records(date_str)

    if not lines:
        print(f"\n  [!] No latency logs found for date '{date_str}'.\n")
        return

    print(f"\n╔════════════════════════════════════════════════════════════════════════════════╗")
    print(f"║  ALFRED LATENCY LOGS — DATE: {date_str:<48} ║")
    print(f"╠════════════════════════════════════════════════════════════════════════════════╣")

    if function_filter:
        print(f"║  Filter: Function '{function_filter}' (showing all matching records)               ║")
        print(f"╚════════════════════════════════════════════════════════════════════════════════╝\n")
        
        filter_lower = function_filter.lower()
        matched = []
        for line in lines:
            if line.startswith("SUMMARY:"):
                # SUMMARY: <function-name>, ...
                parts = line[8:].split(",")
                if parts and filter_lower in parts[0].strip().lower():
                    matched.append(line)
            else:
                parts = line.split(",")
                if parts and filter_lower in parts[0].strip().lower():
                    matched.append(line)

        if not matched:
            print(f"  No records found for function matching '{function_filter}'.\n")
            return

        for m in matched:
            if m.startswith("SUMMARY:"):
                print(f"\033[92m{m}\033[0m")
            else:
                print(f"  {m}")
        print(f"\n  Total records shown: {len(matched)}\n")

    else:
        limit_txt = f"First {lines_limit} lines" if lines_limit > 0 else "All lines"
        print(f"║  Scope: {limit_txt:<68} ║")
        print(f"╚════════════════════════════════════════════════════════════════════════════════╝\n")

        displayed = lines[:lines_limit] if lines_limit > 0 else lines
        for l in displayed:
            if l.startswith("SUMMARY:"):
                print(f"\033[92m{l}\033[0m")
            else:
                print(f"  {l}")

        remaining = len(lines) - len(displayed)
        if remaining > 0:
            print(f"\n  ... ({remaining} more lines omitted. Use --lines {len(lines)} to show all)")
        print(f"\n  Showing {len(displayed)} of {len(lines)} total lines.\n")


def _cli_list():
    """--list: show all recorded dates and storage stats."""
    recorder = LatencyRecorder()
    dates = recorder.get_available_dates()

    print("\n╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                     ALFRED LATENCY LOG ARCHIVES                       ║")
    print("╠═══════════════════════════════════════════════════════════════════════╣")
    if not dates:
        print("║   No latency logs recorded yet.                                       ║")
        print("╚═══════════════════════════════════════════════════════════════════════╝\n")
        return

    print(f"║  {'Date':<14} {'Status':<25} {'Size (KB)':<12}           ║")
    print("╟───────────────────────────────────────────────────────────────────────╢")
    for d in dates:
        size_kb = f"{d['size_bytes'] / 1024:.2f} KB"
        print(f"║  {d['date']:<14} {d['status']:<25} {size_kb:<12}           ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝\n")


def _cli_clean():
    """--clean: force cleanup of old logs."""
    recorder = LatencyRecorder()
    deleted = recorder.cleanup_old(RETENTION_DAYS)
    print(f"\n  Cleaned up {deleted} latency files older than {RETENTION_DAYS} days.\n")


def _cli_help():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                    ALFRED  LATENCY  RECORDER  CLI                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  Usage:                                                                  ║
║    python .\\FILES\\LATENCY_RECORDER.py [options]                          ║
║                                                                          ║
║  Commands & Options:                                                     ║
║    --show <date>           Decompress & display records for YYYY-MM-DD.  ║
║                            (Defaults to first 50 lines if not specified) ║
║                                                                          ║
║    --lines <number>        Number of lines to show with --show (int).    ║
║                            e.g. --show 2026-09-01 --lines 100            ║
║                                                                          ║
║    --function-name <name>  Show all logs and summary for specified       ║
║                            function name irrespective of line limit.     ║
║                            e.g. --show 2026-09-01 --function-name utils  ║
║                                                                          ║
║    --list                  List all available date log files & status.   ║
║                                                                          ║
║    --clean                 Delete records older than 15 days.            ║
║                                                                          ║
║    (no arguments)          Show this help message.                       ║
║                                                                          ║
║  Storage Architecture:                                                   ║
║    Active Logs : logs/latency/YYYY-MM-DD.log                             ║
║    Compressed  : logs/latency/YYYY-MM-DD.log.compressed_logs             ║
║    Format      : <func>, <q_len>, <recv_time>, <out_time>, <dur>s        ║
║    Summary     : SUMMARY: <func>, <avg_q_len>, <avg_duration>s           ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--show", type=str, default=None, help="Date to inspect (YYYY-MM-DD)")
    parser.add_argument("--lines", type=int, default=50, help="Max lines to display")
    parser.add_argument("--function-name", "--function", type=str, default=None, dest="function_name", help="Filter by function name")
    parser.add_argument("--list", action="store_true", help="List all dates")
    parser.add_argument("--clean", action="store_true", help="Clean old records")
    parser.add_argument("--help", "-h", action="store_true", help="Show help")

    args, _ = parser.parse_known_args()

    if args.help:
        _cli_help()
    elif args.list:
        _cli_list()
    elif args.clean:
        _cli_clean()
    elif args.show:
        _cli_show(args.show, lines_limit=args.lines, function_filter=args.function_name)
    elif args.function_name:
        # If --function-name provided without --show, default to today
        today_str = datetime.now().strftime("%Y-%m-%d")
        _cli_show(today_str, lines_limit=args.lines, function_filter=args.function_name)
    else:
        _cli_help()
