"""
LATENCY_RECORDER.py — Performance latency tracker and analyzer for ALFRED.

Key Capabilities:
- Records Query-to-Response Latency before speaking.
- Dual-length documentation: query length and response length tracked side-by-side.
- Groups latencies into content-length buckets:
    - Bucket 1 (1–100 chars): Quick acknowledgments, status, time/date.
    - Bucket 2 (101–250 chars): Short conversational responses, quick recall.
    - Bucket 3 (251–500 chars): Standard assistant answers and explanations.
    - Bucket 4 (501–1000 chars): Detailed explanations and summaries.
    - Bucket 5 (1001+ chars): Deep web scraping, research, multi-paragraph content.
- Historical comparison: Compares the newest latency against the rolling previous 10 latencies
  and against the matching content-length group average.
- Graphical Statistics:
    - Terminal ASCII/Unicode visual charts & sparklines.
    - Native Tkinter visual GUI window (--plot).
    - Auto-generated SVG visual dashboard (logs/latency/stats.svg).
- Batch Zip Archiver:
    - Compresses files older than 7 days in batches of 5 into a single zip file formatted:
      from_DD_MM_YYYY_to_DD_MM_YYYY_alfred_latency_log.zip.
"""

import os
import sys
import time
import atexit
import threading
import functools
import argparse
import zipfile
from datetime import datetime, timedelta
from collections import defaultdict

# ─── Path & Imports ───────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATENCY_DIR = os.path.join(_BASE_DIR, "logs", "latency")
RETENTION_DAYS = 15

if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from FILES.log_compressor import compress_log, decompress_log, read_compressed_log, _read_bytes_payload

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# ─── Content-Length Buckets ───────────────────────────────────────────────────

BUCKETS = [
    ("1-100 chars", 1, 100),
    ("101-250 chars", 101, 250),
    ("251-500 chars", 251, 500),
    ("501-1000 chars", 501, 1000),
    ("1001+ chars", 1001, float("inf")),
]


# 100-character step separations (0 to 1000+ with 100 per separation)
CONTENT_BINS_100 = [
    ("0-100", 0, 100),
    ("101-200", 101, 200),
    ("201-300", 201, 300),
    ("301-400", 301, 400),
    ("401-500", 401, 500),
    ("501-600", 501, 600),
    ("601-700", 601, 700),
    ("701-800", 701, 800),
    ("801-900", 801, 900),
    ("901-1000", 901, 1000),
    ("1001+", 1001, float("inf")),
]


def get_content_bucket(length: int) -> str:
    """Returns the bucket label for a given response character length."""
    for name, low, high in BUCKETS:
        if low <= length <= high:
            return name
    return "1-100 chars" if length <= 100 else "1001+ chars"


def get_content_bin_100(length: int) -> str:
    """Returns the 100-step content length bin label for a given query character length."""
    for name, low, high in CONTENT_BINS_100:
        if low <= length <= high:
            return name
    return "0-100" if length <= 100 else "1001+"


# ─── LatencyRecorder ─────────────────────────────────────────────────────────

class LatencyRecorder:
    """Thread-safe latency tracker, grouping analyzer, and batch archiver."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
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
        
        # Register automatic reorganization, compression, and batch archiving on program exit
        atexit.register(self._on_exit_cleanup)
        self._initialized = True

    def _on_exit_cleanup(self):
        """Runs on program termination: reorganizes active logs, compresses, and archives batches."""
        try:
            self.organize_and_compress_all()
            self.archive_old_batches(min_age_days=7, batch_size=5)
            self.generate_svg_stats()
            self.generate_png_graphs()
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_log_path(self, date_str: str = None) -> str:
        """Active uncompressed log path."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(LATENCY_DIR, f"{date_str}.log")

    def _get_compressed_path(self, date_str: str = None) -> str:
        """Compressed archive path."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(LATENCY_DIR, f"{date_str}.log.compressed_logs")

    # ── Core Recording ────────────────────────────────────────────────────

    def record(self, source: str = "QUERY_RESPONSE", query_length: int = 0,
               response_length: int = 0, query_received_at: float = None,
               output_at: float = None, query: str = None, response: str = None):
        """
        Record a thread-safe latency entry documenting both query and response length.
        Called immediately before speaking.
        """
        now = time.time()
        if output_at is None:
            output_at = now
        if query_received_at is None:
            query_received_at = output_at

        if query and query_length == 0:
            query_length = len(query)
        if response and response_length == 0:
            response_length = len(response)

        duration = max(0.0, output_at - query_received_at)
        bucket = get_content_bucket(response_length)

        req_dt = datetime.fromtimestamp(query_received_at).strftime("%Y-%m-%d %H:%M:%S.%f")[:-1]
        out_dt = datetime.fromtimestamp(output_at).strftime("%Y-%m-%d %H:%M:%S.%f")[:-1]

        # Record format: <source>, <query_length>, <response_length>, <req_dt>, <out_dt>, <duration>s, <bucket>
        line = f"{source}, {query_length}, {response_length}, {req_dt}, {out_dt}, {duration:.5f}s, {bucket}\n"

        log_path = self._get_log_path()
        with self._file_lock:
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
            except Exception:
                pass

    def startup_record(self):
        """Sentinel record marking program startup."""
        now = time.time()
        self.record(
            source="SYSTEM.STARTUP",
            query_length=0,
            response_length=0,
            query_received_at=now,
            output_at=now
        )

    # ── Exit Reorganization & Compression ─────────────────────────────────

    def organize_and_compress(self, log_path: str):
        """Organizes a log file grouped by content-length bucket, appends summaries, and compresses it."""
        if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
            return

        with self._file_lock:
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    raw_lines = f.readlines()

                grouped_records = defaultdict(list)
                for line in raw_lines:
                    line_str = line.strip()
                    if not line_str or line_str.startswith("SUMMARY:") or line_str.startswith("#"):
                        continue

                    parts = [p.strip() for p in line_str.split(",")]
                    # Dual-length format: source, q_len, resp_len, req_dt, out_dt, duration, bucket
                    if len(parts) >= 7:
                        try:
                            q_len = int(parts[1])
                            resp_len = int(parts[2])
                            dur = float(parts[5].rstrip("s"))
                            bucket = parts[6]
                        except ValueError:
                            q_len, resp_len, dur, bucket = 0, 0, 0.0, "1-100 chars"

                        grouped_records[bucket].append({
                            "line": line_str,
                            "query_length": q_len,
                            "response_length": resp_len,
                            "duration": dur
                        })
                    elif len(parts) >= 5:
                        # Legacy format fallback
                        try:
                            q_len = int(parts[1])
                            dur = float(parts[4].rstrip("s"))
                        except ValueError:
                            q_len, dur = 0, 0.0
                        resp_len = q_len
                        bucket = get_content_bucket(resp_len)
                        reconstructed = f"{parts[0]}, {q_len}, {resp_len}, {parts[2]}, {parts[3]}, {dur:.5f}s, {bucket}"
                        grouped_records[bucket].append({
                            "line": reconstructed,
                            "query_length": q_len,
                            "response_length": resp_len,
                            "duration": dur
                        })

                if not grouped_records:
                    return

                # Write reorganized file grouped by bucket
                with open(log_path, "w", encoding="utf-8") as f:
                    # Header
                    f.write("# ALFRED LATENCY LOG — CONTENT-LENGTH GROUPED\n")
                    f.write("# Format: source, query_length, response_length, query_received_at, output_at, duration, bucket\n\n")

                    for b_name, _, _ in BUCKETS:
                        items = grouped_records.get(b_name, [])
                        if not items:
                            continue

                        f.write(f"=== BUCKET: {b_name} ({len(items)} records) ===\n")
                        for it in items:
                            f.write(it["line"] + "\n")

                        # Summaries
                        total = len(items)
                        avg_q = sum(it["query_length"] for it in items) / total
                        avg_r = sum(it["response_length"] for it in items) / total
                        durations = [it["duration"] for it in items]
                        avg_d = sum(durations) / total
                        min_d = min(durations)
                        max_d = max(durations)

                        f.write(f"SUMMARY: {b_name}, count={total}, avg_q_len={avg_q:.1f}, "
                                f"avg_resp_len={avg_r:.1f}, avg_dur={avg_d:.5f}s, "
                                f"min_dur={min_d:.5f}s, max_dur={max_d:.5f}s\n\n")

                # Native log compression (.compressed_logs)
                compress_log(log_path, force=True)
            except Exception:
                pass

    def organize_and_compress_all(self):
        """Scans latency directory for all uncompressed .log files and organizes/compresses them."""
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

    # ── Parsing & Reading ─────────────────────────────────────────────────

    def read_records(self, date_str: str) -> list[str]:
        """Reads all lines for a given date, archive name, or zip archive."""
        # 1. Direct zip archive request
        if date_str.endswith(".zip"):
            zip_path = os.path.join(LATENCY_DIR, date_str) if not os.path.isabs(date_str) else date_str
            if os.path.exists(zip_path):
                lines = []
                try:
                    with zipfile.ZipFile(zip_path, "r") as zf:
                        for name in sorted(zf.namelist()):
                            raw = zf.read(name)
                            decomp = _read_bytes_payload(raw)
                            if not decomp:
                                try:
                                    decomp = raw.decode("utf-8", errors="replace")
                                except Exception:
                                    decomp = ""
                            if decomp:
                                lines.extend([l.rstrip("\r\n") for l in decomp.splitlines() if l.strip()])
                except Exception:
                    pass
                return lines

        # 2. Check active uncompressed log
        log_path = self._get_log_path(date_str)
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                return [line.rstrip("\r\n") for line in f if line.strip()]

        # 3. Check standalone compressed log
        comp_path = self._get_compressed_path(date_str)
        if os.path.exists(comp_path):
            decompressed = read_compressed_log(comp_path)
            if decompressed:
                return [line.rstrip("\r\n") for line in decompressed.splitlines() if line.strip()]

        # 4. Fallback: Search inside any zip archives in LATENCY_DIR for this date
        if os.path.exists(LATENCY_DIR):
            for item in os.listdir(LATENCY_DIR):
                if item.endswith(".zip"):
                    zip_p = os.path.join(LATENCY_DIR, item)
                    try:
                        with zipfile.ZipFile(zip_p, "r") as zf:
                            for name in zf.namelist():
                                if date_str in name:
                                    raw = zf.read(name)
                                    decomp = _read_bytes_payload(raw)
                                    if not decomp:
                                        try:
                                            decomp = raw.decode("utf-8", errors="replace")
                                        except Exception:
                                            decomp = ""
                                    if decomp:
                                        return [l.rstrip("\r\n") for l in decomp.splitlines() if l.strip()]
                    except Exception:
                        pass

        return []

    def _parse_record_line(self, line: str) -> dict | None:
        """Parses a single latency log line into a record dict using query length as primary indicator."""
        line_str = line.strip()
        if not line_str or line_str.startswith("#") or line_str.startswith("SUMMARY:") or line_str.startswith("==="):
            return None

        parts = [p.strip() for p in line_str.split(",")]
        # Dual-length format: source, query_length, response_length, req_dt, out_dt, duration, bucket
        if len(parts) >= 7:
            try:
                ql = int(parts[1])
                rl = int(parts[2])
                dur = float(parts[5].rstrip("s"))
                bucket = parts[6]
            except ValueError:
                return None

            return {
                "source": parts[0],
                "query_length": ql,
                "response_length": rl,
                "req_dt": parts[3],
                "out_dt": parts[4],
                "duration": dur,
                "bucket": bucket,
                "bin_100": get_content_bin_100(ql)
            }
        elif len(parts) >= 5:
            # Legacy format fallback
            try:
                ql = int(parts[1])
                dur = float(parts[4].rstrip("s"))
            except ValueError:
                return None

            return {
                "source": parts[0],
                "query_length": ql,
                "response_length": ql,
                "req_dt": parts[2],
                "out_dt": parts[3],
                "duration": dur,
                "bucket": get_content_bucket(ql),
                "bin_100": get_content_bin_100(ql)
            }
        return None

    def get_all_parsed_records(self, limit: int = None, include_zips: bool = True) -> list[dict]:
        """
        Returns all parsed records across available active logs, compressed logs, and zip archives.
        Ensures query length is the primary context indicator and historical data is fully preserved.
        """
        dates = self.get_available_dates()
        all_records = []

        # Pass 1: Standalone active and compressed daily logs
        for d_meta in dates:
            d_name = d_meta["date"]
            if d_name.endswith(".zip"):
                continue
            lines = self.read_records(d_name)
            for line in lines:
                rec = self._parse_record_line(line)
                if rec:
                    all_records.append(rec)
            if limit and len(all_records) >= limit:
                return all_records[:limit]

        # Pass 2: Archived batch zip files
        if include_zips:
            for d_meta in dates:
                d_name = d_meta["date"]
                if not d_name.endswith(".zip"):
                    continue
                lines = self.read_records(d_name)
                for line in lines:
                    rec = self._parse_record_line(line)
                    if rec:
                        all_records.append(rec)
                if limit and len(all_records) >= limit:
                    return all_records[:limit]

        return all_records[:limit] if limit else all_records

    # ── Function 1: Previous 10 Latencies & Comparison ────────────────────

    def get_recent_comparisons(self, limit: int = 10) -> dict:
        """
        Provides the last `limit` latencies recorded, moving average, and comparison data.
        """
        records = self.get_all_parsed_records(limit=limit + 1)
        if not records:
            return {"error": "No recorded latencies found."}

        newest = records[0]
        prev_records = records[1:limit + 1] if len(records) > 1 else [newest]

        durations = [r["duration"] for r in prev_records]
        avg_prev = sum(durations) / len(durations) if durations else newest["duration"]

        # Delta vs rolling 10-average
        delta_pct = ((newest["duration"] - avg_prev) / avg_prev * 100.0) if avg_prev > 0 else 0.0

        # Same-bucket comparison
        same_bucket = [r["duration"] for r in records if r["bucket"] == newest["bucket"]]
        avg_bucket = sum(same_bucket) / len(same_bucket) if same_bucket else newest["duration"]
        delta_bucket_pct = ((newest["duration"] - avg_bucket) / avg_bucket * 100.0) if avg_bucket > 0 else 0.0

        return {
            "newest": newest,
            "previous_10": prev_records[:10],
            "avg_previous_10": avg_prev,
            "delta_percent_vs_avg": delta_pct,
            "same_bucket_avg": avg_bucket,
            "delta_percent_vs_bucket": delta_bucket_pct,
            "min_duration": min(durations) if durations else newest["duration"],
            "max_duration": max(durations) if durations else newest["duration"],
        }

    # ── Function 2: Graphical Statistics ──────────────────────────────────

    def show_graphical_stats(self, mode: str = "cli"):
        """Displays visual statistics (ASCII/Unicode in CLI or native Tkinter GUI window)."""
        records = self.get_all_parsed_records()
        if not records:
            print("\n  [!] No latency records found to generate statistics.\n")
            return

        # Calculate bucket statistics
        bucket_stats = {}
        for b_name, _, _ in BUCKETS:
            matched = [r for r in records if r["bucket"] == b_name]
            count = len(matched)
            durations = [r["duration"] for r in matched]
            avg_d = (sum(durations) / count) if count > 0 else 0.0
            min_d = min(durations) if count > 0 else 0.0
            max_d = max(durations) if count > 0 else 0.0
            avg_resp = (sum(r["response_length"] for r in matched) / count) if count > 0 else 0
            bucket_stats[b_name] = {
                "count": count,
                "avg_duration": avg_d,
                "min_duration": min_d,
                "max_duration": max_d,
                "avg_response_len": avg_resp
            }

        if mode == "gui":
            self._render_tkinter_gui(bucket_stats, records[:30])
        else:
            self._render_ascii_stats(bucket_stats, records[:15])

    def _render_ascii_stats(self, bucket_stats: dict, recent_records: list):
        """Renders ASCII bar charts and sparklines in console."""
        max_avg = max((s["avg_duration"] for s in bucket_stats.values()), default=1.0)
        if max_avg <= 0:
            max_avg = 1.0

        bar_width = 38

        print("\n╔════════════════════════════════════════════════════════════════════════════════════╗")
        print("║                   ALFRED LATENCY GRAPHICAL STATS (BY BUCKET)                       ║")
        print("╠════════════════════════════════════════════════════════════════════════════════════╣")
        print(f"║  {'Bucket':<15} {'Count':<7} {'Avg Latency':<12} {'Visual Distribution':<{bar_width}}  ║")
        print("╟────────────────────────────────────────────────────────────────────────────────────╢")

        for b_name, _, _ in BUCKETS:
            st = bucket_stats[b_name]
            filled_len = int((st["avg_duration"] / max_avg) * bar_width) if st["count"] > 0 else 0
            bar = "█" * filled_len + "░" * (bar_width - filled_len)
            avg_str = f"{st['avg_duration']:.3f}s" if st["count"] > 0 else "N/A"
            print(f"║  {b_name:<15} {st['count']:<7} {avg_str:<12} {bar}  ║")

        print("╚════════════════════════════════════════════════════════════════════════════════════╝\n")

        # Sparkline / trend of recent records
        if recent_records:
            print("─" * 84)
            print("  Recent Query Latency Trend (Newest to Oldest):")
            trend_str = " -> ".join([f"{r['duration']:.2f}s ({r['bucket']})" for r in recent_records[:8]])
            print(f"  {trend_str}")
            print("─" * 84 + "\n")

    def _render_tkinter_gui(self, bucket_stats: dict, recent_records: list):
        """Renders graphical bar charts using built-in Python Tkinter."""
        try:
            import tkinter as tk
        except ImportError:
            print("  [!] Tkinter is not available. Falling back to CLI mode.")
            self._render_ascii_stats(bucket_stats, recent_records)
            return

        root = tk.Tk()
        root.title("ALFRED Latency Statistics")
        root.geometry("820x520")
        root.configure(bg="#1e1e2e")

        # Header
        title = tk.Label(root, text="ALFRED Latency Performance & Content Buckets",
                         font=("Helvetica", 14, "bold"), fg="#cdd6f4", bg="#1e1e2e")
        title.pack(pady=12)

        canvas = tk.Canvas(root, width=760, height=420, bg="#181825", highlightthickness=0)
        canvas.pack(pady=10)

        # Draw Bar Chart
        y_offset = 35
        max_avg = max((s["avg_duration"] for s in bucket_stats.values()), default=1.0) or 1.0

        canvas.create_text(20, 15, text="Content-Length Bucket Latency (Avg Seconds)",
                           anchor="w", fill="#89b4fa", font=("Helvetica", 10, "bold"))

        for b_name, _, _ in BUCKETS:
            st = bucket_stats[b_name]
            canvas.create_text(25, y_offset + 12, text=f"{b_name} ({st['count']} queries)",
                               anchor="w", fill="#bac2de", font=("Helvetica", 9))

            # Bar background
            canvas.create_rectangle(220, y_offset, 650, y_offset + 24, fill="#313244", outline="")
            
            # Bar fill
            ratio = (st["avg_duration"] / max_avg) if st["count"] > 0 else 0
            bar_len = int(ratio * 430)
            if bar_len > 0:
                canvas.create_rectangle(220, y_offset, 220 + bar_len, y_offset + 24, fill="#a6e3a1", outline="")

            # Text label
            dur_txt = f"{st['avg_duration']:.3f}s (min: {st['min_duration']:.2f}s, max: {st['max_duration']:.2f}s)" if st["count"] > 0 else "No data"
            canvas.create_text(220 + bar_len + 8, y_offset + 12, text=dur_txt, anchor="w", fill="#cdd6f4", font=("Helvetica", 9))

            y_offset += 45

        # Timeline plot of recent 15 queries
        y_offset += 20
        canvas.create_text(20, y_offset, text="Recent Query Latency Timeline:", anchor="w", fill="#f9e2af", font=("Helvetica", 10, "bold"))
        y_offset += 25

        if recent_records:
            pts = []
            x_start, x_step = 40, 48
            max_r = max((r["duration"] for r in recent_records[:15]), default=1.0) or 1.0
            for i, r in enumerate(reversed(recent_records[:15])):
                cx = x_start + (i * x_step)
                cy = (y_offset + 60) - int((r["duration"] / max_r) * 50)
                pts.append((cx, cy, r["duration"]))

            # Draw lines and dots
            for i in range(len(pts) - 1):
                canvas.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], fill="#f38ba8", width=2)
            for cx, cy, d in pts:
                canvas.create_oval(cx-3, cy-3, cx+3, cy+3, fill="#fab387", outline="#181825")
                canvas.create_text(cx, cy - 8, text=f"{d:.1f}s", fill="#cdd6f4", font=("Helvetica", 7))

        root.mainloop()

    def generate_svg_stats(self, output_path: str = None) -> str:
        """Generates an exportable SVG graphical chart saved to disk."""
        if output_path is None:
            output_path = os.path.join(LATENCY_DIR, "stats.svg")

        records = self.get_all_parsed_records()
        if not records:
            return ""

        bucket_stats = {}
        for b_name, _, _ in BUCKETS:
            matched = [r for r in records if r["bucket"] == b_name]
            count = len(matched)
            durations = [r["duration"] for r in matched]
            avg_d = (sum(durations) / count) if count > 0 else 0.0
            bucket_stats[b_name] = {"count": count, "avg_duration": avg_d}

        max_avg = max((s["avg_duration"] for s in bucket_stats.values()), default=1.0) or 1.0

        svg_lines = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="700" height="340" style="background:#181825; font-family:sans-serif;">',
            '  <text x="20" y="30" fill="#cdd6f4" font-size="16" font-weight="bold">ALFRED Latency Statistics</text>',
            '  <text x="20" y="52" fill="#a6adc8" font-size="12">Grouped by Content-Length Buckets</text>'
        ]

        y = 80
        for b_name, _, _ in BUCKETS:
            st = bucket_stats[b_name]
            bar_w = int((st["avg_duration"] / max_avg) * 360) if st["count"] > 0 else 0
            svg_lines.append(f'  <text x="20" y="{y+16}" fill="#cdd6f4" font-size="12">{b_name} ({st["count"]})</text>')
            svg_lines.append(f'  <rect x="180" y="{y}" width="360" height="24" rx="4" fill="#313244"/>')
            if bar_w > 0:
                svg_lines.append(f'  <rect x="180" y="{y}" width="{bar_w}" height="24" rx="4" fill="#a6e3a1"/>')
            avg_txt = f"{st['avg_duration']:.3f}s" if st["count"] > 0 else "0.000s"
            svg_lines.append(f'  <text x="{180 + bar_w + 10}" y="{y+16}" fill="#cdd6f4" font-size="12">{avg_txt}</text>')
            y += 45

        svg_lines.append('</svg>')

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(svg_lines))
            return output_path
        except Exception:
            return ""

    # ── High-Resolution PNG Graphical Stat Maker ──────────────────────────

    def generate_png_graphs(self, output_dir: str = None, graph_type: str = "all") -> dict[str, str]:
        """
        Generates high-resolution PNG graphical stat charts with:
        - Base Axis (X): Content Length (0-1000+ with 100 per separation in between, based on query length).
        - Upward Axis (Y): Time taken in seconds.
        - Historical data: Fully includes active logs, standalone compressed logs, and archived zip files.
        - 3 types of graphical output:
            1. Line graph (mean, median, p95 trends with shaded IQR band).
            2. Box/Block/Histogram graph (box-and-whisker distribution + query volume histogram).
            3. Scatter plot with polynomial scaling trendline.
            4. Combined 3-in-1 overview dashboard.
        """
        if not HAS_MATPLOTLIB:
            print("  [!] Matplotlib is not available. Please install matplotlib to generate PNG graphs.")
            return {}

        if output_dir is None:
            output_dir = LATENCY_DIR
        os.makedirs(output_dir, exist_ok=True)

        records = self.get_all_parsed_records(include_zips=True)
        if not records:
            print("  [!] No latency records found to generate PNG graphs.")
            return {}

        g_type = graph_type.lower().strip()
        generated = {}

        if g_type in ("all", "line"):
            path = os.path.join(output_dir, "latency_line_graph.png")
            if self._render_line_graph_png(records, path):
                generated["line"] = path

        if g_type in ("all", "box", "block", "histogram", "hist"):
            path = os.path.join(output_dir, "latency_box_hist_graph.png")
            if self._render_box_hist_graph_png(records, path):
                generated["box"] = path

        if g_type in ("all", "scatter", "other", "trend"):
            path = os.path.join(output_dir, "latency_scatter_trend_graph.png")
            if self._render_scatter_trend_graph_png(records, path):
                generated["scatter"] = path

        if g_type in ("all", "dashboard"):
            path = os.path.join(output_dir, "latency_combined_dashboard.png")
            if self._render_combined_dashboard_png(records, path):
                generated["dashboard"] = path

        return generated

    def _render_line_graph_png(self, records: list[dict], output_path: str) -> bool:
        """
        Renders Line Graph:
        - Base Axis (X): Content Length (0-1000+ with 100 separation in between).
        - Upward Axis (Y): Time taken (Seconds).
        - Metrics: Mean latency, Median latency, 95th Percentile latency, and IQR band.
        """
        try:
            bin_data = defaultdict(list)
            for r in records:
                bin_data[r.get("bin_100", "0-100")].append(r["duration"])

            x_indices = np.arange(len(CONTENT_BINS_100))
            bin_names = [b[0] for b in CONTENT_BINS_100]

            counts = []
            means = []
            medians = []
            p25s = []
            p75s = []
            p95s = []

            for name, _, _ in CONTENT_BINS_100:
                vals = bin_data.get(name, [])
                cnt = len(vals)
                counts.append(cnt)
                if cnt > 0:
                    means.append(float(np.mean(vals)))
                    medians.append(float(np.median(vals)))
                    p25s.append(float(np.percentile(vals, 25)))
                    p75s.append(float(np.percentile(vals, 75)))
                    p95s.append(float(np.percentile(vals, 95)))
                else:
                    means.append(0.0)
                    medians.append(0.0)
                    p25s.append(0.0)
                    p75s.append(0.0)
                    p95s.append(0.0)

            # High-contrast modern dark theme
            fig, ax = plt.subplots(figsize=(14, 7.5), dpi=300, facecolor="#0f172a")
            ax.set_facecolor("#1e293b")

            # Grid lines
            ax.grid(True, linestyle="--", linewidth=0.7, color="#334155", alpha=0.8, zorder=1)

            # Shaded IQR band (25th to 75th percentile)
            ax.fill_between(x_indices, p25s, p75s, color="#38bdf8", alpha=0.18, label="25th–75th Percentile Band (IQR)", zorder=2)

            # Trend lines
            ax.plot(x_indices, p95s, color="#f59e0b", linestyle=":", linewidth=2.0, marker="^", markersize=6, label="95th Percentile Latency (p95)", zorder=3)
            ax.plot(x_indices, medians, color="#c084fc", linestyle="--", linewidth=2.2, marker="s", markersize=6, label="Median Latency (p50)", zorder=4)
            ax.plot(x_indices, means, color="#38bdf8", linestyle="-", linewidth=2.8, marker="o", markersize=8, label="Mean Latency (Average)", zorder=5)

            # Annotate values above points where count > 0
            for idx in x_indices:
                if counts[idx] > 0:
                    m_val = means[idx]
                    ax.annotate(f"{m_val:.2f}s", xy=(idx, m_val), xytext=(0, 9), textcoords="offset points",
                                ha="center", va="bottom", color="#f8fafc", fontsize=8.5, fontweight="bold",
                                bbox=dict(boxstyle="round,pad=0.2", facecolor="#0284c7", edgecolor="none", alpha=0.75), zorder=6)

            # Axes and Ticks
            x_labels_formatted = [f"{name}\n(n={counts[i]})" for i, (name, _, _) in enumerate(CONTENT_BINS_100)]
            ax.set_xticks(x_indices)
            ax.set_xticklabels(x_labels_formatted, color="#cbd5e1", fontsize=9.5, fontweight="normal")

            # Dynamic Y-limit to keep detail visible without extreme outlier distortion
            valid_p95 = [p for p in p95s if p > 0]
            valid_means = [m for m in means if m > 0]
            max_y_ref = max(valid_p95 + valid_means, default=5.0)
            y_limit = min(max(max_y_ref * 1.35, 4.0), 35.0)
            ax.set_ylim(0, y_limit)
            ax.tick_params(colors="#cbd5e1", which="both", labelsize=9.5)

            # Titles & Labels
            ax.set_xlabel("Content Length (Query Characters) — 100-character Separation [0 to 1000+]", color="#f8fafc", fontsize=12, fontweight="bold", labelpad=12)
            ax.set_ylabel("Time Taken (Seconds)", color="#f8fafc", fontsize=12, fontweight="bold", labelpad=12)
            ax.set_title("ALFRED Latency Performance — Line Graph Trend (Content Length vs Time Taken)", color="#f8fafc", fontsize=14, fontweight="bold", pad=15)

            # Subtitle & Total records banner
            total_records = len(records)
            ax.text(0.015, 0.96, f"Total Historical Records: {total_records:,} (All Active, Compressed & Zipped Logs Included)",
                    transform=ax.transAxes, color="#94a3b8", fontsize=9.5, va="top",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#0f172a", edgecolor="#334155", alpha=0.8))

            # Legend
            legend = ax.legend(loc="upper right", frameon=True, facecolor="#0f172a", edgecolor="#334155", fontsize=9.5)
            for text in legend.get_texts():
                text.set_color("#e2e8f0")

            for spine in ax.spines.values():
                spine.set_color("#475569")
                spine.set_linewidth(1.0)

            plt.tight_layout()
            fig.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            return True
        except Exception as e:
            print(f"  [!] Failed to render line graph: {e}")
            return False

    def _render_box_hist_graph_png(self, records: list[dict], output_path: str) -> bool:
        """
        Renders Box/Block/Histogram Graphical:
        - Base Axis (X): Content Length (0-1000+ with 100 separation in between).
        - Upward Axis (Y): Time taken (Seconds) on top boxplot; Query Count on bottom histogram.
        - Metrics: Full IQR box distribution, medians, means, outliers, and query frequency blocks.
        """
        try:
            bin_data = defaultdict(list)
            for r in records:
                bin_data[r.get("bin_100", "0-100")].append(r["duration"])

            x_indices = np.arange(len(CONTENT_BINS_100))
            box_durations = [bin_data.get(name, [0.0]) for name, _, _ in CONTENT_BINS_100]
            counts = [len(bin_data.get(name, [])) for name, _, _ in CONTENT_BINS_100]

            fig, (ax_box, ax_hist) = plt.subplots(
                2, 1, figsize=(14, 9), dpi=300, facecolor="#0f172a", sharex=True,
                gridspec_kw={"height_ratios": [2.2, 1.0], "hspace": 0.12}
            )

            for ax in (ax_box, ax_hist):
                ax.set_facecolor("#1e293b")
                ax.grid(True, linestyle="--", linewidth=0.7, color="#334155", alpha=0.8, zorder=1)
                for spine in ax.spines.values():
                    spine.set_color("#475569")
                    spine.set_linewidth(1.0)

            # ── Top Subplot: Box & Whisker Plot ──
            bp = ax_box.boxplot(
                box_durations, positions=x_indices, patch_artist=True, widths=0.52, showmeans=True,
                meanprops=dict(marker="D", markeredgecolor="#10b981", markerfacecolor="#10b981", markersize=6),
                medianprops=dict(color="#facc15", linewidth=2.4),
                boxprops=dict(facecolor="#0284c7", edgecolor="#38bdf8", alpha=0.85, linewidth=1.2),
                whiskerprops=dict(color="#94a3b8", linewidth=1.5),
                capprops=dict(color="#94a3b8", linewidth=1.5),
                flierprops=dict(marker="o", markersize=3.5, markerfacecolor="#f43f5e", markeredgecolor="none", alpha=0.45)
            )

            # Top Y limit (outlier aware)
            all_durs = [r["duration"] for r in records]
            p99_val = float(np.percentile(all_durs, 99)) if all_durs else 5.0
            ax_box.set_ylim(0, min(max(p99_val * 1.3, 10.0), 45.0))
            ax_box.set_ylabel("Time Taken (Seconds)", color="#f8fafc", fontsize=11.5, fontweight="bold", labelpad=10)
            ax_box.set_title("ALFRED Latency Performance — Box Plot & Query Volume Histogram\nDistribution & Frequency by 100-character Content Length Bins",
                             color="#f8fafc", fontsize=13.5, fontweight="bold", pad=12)
            ax_box.tick_params(colors="#cbd5e1", which="both", labelsize=9.5)

            # Custom Legend for Boxplot
            box_legend_elements = [
                plt.Line2D([0], [0], color="#facc15", lw=2.4, label="Median Latency"),
                plt.Line2D([0], [0], marker="D", color="#10b981", lw=0, markersize=6, label="Mean Latency"),
                plt.Line2D([0], [0], color="#0284c7", lw=6, label="IQR Box (25th-75th %)"),
                plt.Line2D([0], [0], marker="o", color="#f43f5e", lw=0, markersize=4, label="Outliers")
            ]
            box_leg = ax_box.legend(handles=box_legend_elements, loc="upper right", frameon=True, facecolor="#0f172a", edgecolor="#334155", fontsize=9)
            for text in box_leg.get_texts():
                text.set_color("#e2e8f0")

            # ── Bottom Subplot: Query Volume Histogram / Block Bar ──
            bars = ax_hist.bar(x_indices, counts, width=0.52, color="#8b5cf6", edgecolor="#c4b5fd", alpha=0.88, zorder=3)
            ax_hist.set_ylabel("Query Count", color="#f8fafc", fontsize=11.5, fontweight="bold", labelpad=10)
            ax_hist.set_xlabel("Content Length (Query Characters) — 100-character Separation [0 to 1000+]", color="#f8fafc", fontsize=11.5, fontweight="bold", labelpad=10)

            # Annotate counts above bars
            max_cnt = max(counts, default=1)
            ax_hist.set_ylim(0, max_cnt * 1.18)
            for bar in bars:
                h = bar.get_height()
                ax_hist.annotate(f"{h:,}", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 3),
                                 textcoords="offset points", ha="center", va="bottom", color="#f1f5f9", fontsize=8.5, fontweight="bold")

            x_labels = [b[0] for b in CONTENT_BINS_100]
            ax_hist.set_xticks(x_indices)
            ax_hist.set_xticklabels(x_labels, color="#cbd5e1", fontsize=9.5, fontweight="normal")
            ax_hist.tick_params(colors="#cbd5e1", which="both", labelsize=9.5)

            fig.subplots_adjust(left=0.07, right=0.96, top=0.92, bottom=0.08, hspace=0.15)
            fig.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            return True
        except Exception as e:
            print(f"  [!] Failed to render box/histogram graph: {e}")
            return False

    def _render_scatter_trend_graph_png(self, records: list[dict], output_path: str) -> bool:
        """
        Renders Scatter Plot with Polynomial Latency Scaling Trend:
        - Base Axis (X): Exact Content Length (0 to 1000+ with 100 separation in between).
        - Upward Axis (Y): Time taken (Seconds).
        - Features: Individual query latency points, density visualization, and polynomial fit curve.
        """
        try:
            qls = np.array([r["query_length"] for r in records])
            durs = np.array([r["duration"] for r in records])

            # Position values > 1000 into the 1000+ zone at x=1050
            qls_plot = np.clip(qls, 0, 1050)

            fig, ax = plt.subplots(figsize=(14, 7.5), dpi=300, facecolor="#0f172a")
            ax.set_facecolor("#1e293b")
            ax.grid(True, linestyle="--", linewidth=0.7, color="#334155", alpha=0.8, zorder=1)

            # Scatter points
            ax.scatter(qls_plot, durs, color="#38bdf8", alpha=0.35, s=22, edgecolors="none",
                       label=f"Individual Recorded Queries (n={len(records):,})", zorder=3)

            # Fit polynomial trendline (degree 2) on non-idle queries (below 99.2th percentile)
            p99_cut = float(np.percentile(durs, 99.2)) if len(durs) > 0 else 10.0
            mask = durs <= p99_cut
            if np.sum(mask) > 10:
                poly_coeffs = np.polyfit(qls_plot[mask], durs[mask], 2)
                poly_fn = np.poly1d(poly_coeffs)
                x_trend = np.linspace(0, 1050, 200)
                y_trend = np.clip(poly_fn(x_trend), 0, None)
                ax.plot(x_trend, y_trend, color="#f43f5e", linewidth=3.2, label="Polynomial Latency Scaling Trend", zorder=5)

            # Overall mean reference line
            overall_mean = float(np.mean(durs))
            ax.axhline(overall_mean, color="#10b981", linestyle="--", linewidth=1.8, label=f"Overall Dataset Mean ({overall_mean:.2f}s)", zorder=4)

            # X-axis ticks: 0 to 1000 with 100 separation in between + 1000+ indicator
            x_ticks = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1050]
            x_tick_labels = ["0", "100", "200", "300", "400", "500", "600", "700", "800", "900", "1000", "1000+"]
            ax.set_xticks(x_ticks)
            ax.set_xticklabels(x_tick_labels, color="#cbd5e1", fontsize=9.5, fontweight="normal")
            ax.set_xlim(-20, 1070)

            # Y-axis limits (outlier focused)
            y_max_plot = min(max(p99_cut * 1.35, 10.0), 50.0)
            ax.set_ylim(0, y_max_plot)
            ax.tick_params(colors="#cbd5e1", which="both", labelsize=9.5)

            # Titles & Labels
            ax.set_xlabel("Content Length (Query Characters) — 100-character Separation [0 to 1000+]", color="#f8fafc", fontsize=12, fontweight="bold", labelpad=12)
            ax.set_ylabel("Time Taken (Seconds)", color="#f8fafc", fontsize=12, fontweight="bold", labelpad=12)
            ax.set_title("ALFRED Latency Performance — Scatter Plot & Empirical Scaling Trend\nExact Content Length vs Time Taken",
                         color="#f8fafc", fontsize=14, fontweight="bold", pad=15)

            # Legend
            leg = ax.legend(loc="upper right", frameon=True, facecolor="#0f172a", edgecolor="#334155", fontsize=9.5)
            for text in leg.get_texts():
                text.set_color("#e2e8f0")

            for spine in ax.spines.values():
                spine.set_color("#475569")
                spine.set_linewidth(1.0)

            plt.tight_layout()
            fig.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            return True
        except Exception as e:
            print(f"  [!] Failed to render scatter trend graph: {e}")
            return False

    def _render_combined_dashboard_png(self, records: list[dict], output_path: str) -> bool:
        """
        Renders Composite 3-in-1 Dashboard:
        Combines Line Graph, Box Plot, Scatter Plot, and Summary Metrics into a single multi-panel image.
        """
        try:
            fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor="#0f172a")

            for row in axs:
                for ax in row:
                    ax.set_facecolor("#1e293b")
                    ax.grid(True, linestyle="--", linewidth=0.7, color="#334155", alpha=0.8, zorder=1)
                    for spine in ax.spines.values():
                        spine.set_color("#475569")
                        spine.set_linewidth(1.0)
                    ax.tick_params(colors="#cbd5e1", which="both", labelsize=8.5)

            bin_data = defaultdict(list)
            for r in records:
                bin_data[r.get("bin_100", "0-100")].append(r["duration"])

            x_indices = np.arange(len(CONTENT_BINS_100))
            bin_labels = [b[0] for b in CONTENT_BINS_100]

            counts = [len(bin_data.get(b[0], [])) for b in CONTENT_BINS_100]
            means = [float(np.mean(bin_data[b[0]])) if bin_data[b[0]] else 0.0 for b in CONTENT_BINS_100]
            medians = [float(np.median(bin_data[b[0]])) if bin_data[b[0]] else 0.0 for b in CONTENT_BINS_100]
            p95s = [float(np.percentile(bin_data[b[0]], 95)) if bin_data[b[0]] else 0.0 for b in CONTENT_BINS_100]

            # ── Panel 1: Line Graph ──
            ax1 = axs[0, 0]
            ax1.plot(x_indices, p95s, color="#f59e0b", linestyle=":", linewidth=1.8, marker="^", markersize=5, label="p95 Latency")
            ax1.plot(x_indices, medians, color="#c084fc", linestyle="--", linewidth=2.0, marker="s", markersize=5, label="Median Latency")
            ax1.plot(x_indices, means, color="#38bdf8", linestyle="-", linewidth=2.5, marker="o", markersize=6, label="Mean Latency")
            ax1.set_xticks(x_indices)
            ax1.set_xticklabels(bin_labels, rotation=35, ha="right")
            ax1.set_ylabel("Time Taken (Seconds)", color="#f8fafc", fontweight="bold", fontsize=10)
            ax1.set_title("1. Line Graph Trend", color="#f8fafc", fontweight="bold", fontsize=12)
            leg1 = ax1.legend(loc="upper right", facecolor="#0f172a", edgecolor="#334155", fontsize=8.5)
            for t in leg1.get_texts(): t.set_color("#e2e8f0")

            # ── Panel 2: Box Plot ──
            ax2 = axs[0, 1]
            box_durations = [bin_data.get(name, [0.0]) for name, _, _ in CONTENT_BINS_100]
            ax2.boxplot(
                box_durations, positions=x_indices, patch_artist=True, widths=0.52, showmeans=True,
                meanprops=dict(marker="D", markeredgecolor="#10b981", markerfacecolor="#10b981", markersize=5),
                medianprops=dict(color="#facc15", linewidth=2.0),
                boxprops=dict(facecolor="#0284c7", edgecolor="#38bdf8", alpha=0.85),
                whiskerprops=dict(color="#94a3b8", linewidth=1.2),
                capprops=dict(color="#94a3b8", linewidth=1.2),
                flierprops=dict(marker="o", markersize=2.5, markerfacecolor="#f43f5e", markeredgecolor="none", alpha=0.35)
            )
            all_durs = [r["duration"] for r in records]
            p99_cut = float(np.percentile(all_durs, 99)) if all_durs else 5.0
            ax2.set_ylim(0, min(max(p99_cut * 1.3, 10.0), 45.0))
            ax2.set_xticks(x_indices)
            ax2.set_xticklabels(bin_labels, rotation=35, ha="right")
            ax2.set_ylabel("Time Taken (Seconds)", color="#f8fafc", fontweight="bold", fontsize=10)
            ax2.set_title("2. Box & Whisker Distribution", color="#f8fafc", fontweight="bold", fontsize=12)

            # ── Panel 3: Scatter Plot & Trendline ──
            ax3 = axs[1, 0]
            qls = np.array([min(r["query_length"], 1050) for r in records])
            durs = np.array([r["duration"] for r in records])
            ax3.scatter(qls, durs, color="#38bdf8", alpha=0.3, s=16, edgecolors="none", label="Queries")
            mask = durs <= p99_cut
            if np.sum(mask) > 10:
                p_c = np.polyfit(qls[mask], durs[mask], 2)
                p_f = np.poly1d(p_c)
                x_fit = np.linspace(0, 1050, 150)
                ax3.plot(x_fit, np.clip(p_f(x_fit), 0, None), color="#f43f5e", linewidth=2.8, label="Scaling Trend")
            ax3.set_xticks([0, 200, 400, 600, 800, 1000, 1050])
            ax3.set_xticklabels(["0", "200", "400", "600", "800", "1000", "1000+"])
            ax3.set_ylim(0, min(max(p99_cut * 1.3, 10.0), 45.0))
            ax3.set_xlabel("Content Length (Query Characters)", color="#f8fafc", fontweight="bold", fontsize=10)
            ax3.set_ylabel("Time Taken (Seconds)", color="#f8fafc", fontweight="bold", fontsize=10)
            ax3.set_title("3. Scatter Plot & Scaling Fit", color="#f8fafc", fontweight="bold", fontsize=12)
            leg3 = ax3.legend(loc="upper right", facecolor="#0f172a", edgecolor="#334155", fontsize=8.5)
            for t in leg3.get_texts(): t.set_color("#e2e8f0")

            # ── Panel 4: Query Volume & Key Metrics Summary ──
            ax4 = axs[1, 1]
            bars = ax4.bar(x_indices, counts, width=0.52, color="#8b5cf6", edgecolor="#c4b5fd", alpha=0.88, zorder=3)
            ax4.set_xticks(x_indices)
            ax4.set_xticklabels(bin_labels, rotation=35, ha="right")
            ax4.set_ylabel("Query Count", color="#f8fafc", fontweight="bold", fontsize=10)
            ax4.set_xlabel("Content Length (Query Characters)", color="#f8fafc", fontweight="bold", fontsize=10)
            ax4.set_title("4. Sample Volume & Key Summary Metrics", color="#f8fafc", fontweight="bold", fontsize=12)

            # Metrics text card
            mean_all = float(np.mean(all_durs))
            median_all = float(np.median(all_durs))
            p95_all = float(np.percentile(all_durs, 95))
            summary_txt = (
                f"Total Records : {len(records):,}\n"
                f"Mean Latency  : {mean_all:.3f}s\n"
                f"Median Latency: {median_all:.3f}s\n"
                f"p95 Latency   : {p95_all:.3f}s"
            )
            ax4.text(0.97, 0.94, summary_txt, transform=ax4.transAxes, color="#f8fafc",
                     fontsize=9, va="top", ha="right", fontfamily="monospace",
                     bbox=dict(boxstyle="round,pad=0.5", facecolor="#0f172a", edgecolor="#8b5cf6", alpha=0.9))

            fig.suptitle("ALFRED Latency Performance — Comprehensive Graphical Dashboard\nContent Length (0–1000+ with 100 separation) vs Time Taken",
                         color="#f8fafc", fontsize=15, fontweight="bold", y=0.98)

            plt.tight_layout(rect=[0, 0, 1, 0.96])
            fig.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            return True
        except Exception as e:
            print(f"  [!] Failed to render combined dashboard: {e}")
            return False

    # ── Function 3: Batch Zip Archiver (>7 Days Old in Groups of 5) ───────

    def archive_old_batches(self, min_age_days: int = 7, batch_size: int = 5) -> list[str]:
        """
        Scans for files older than min_age_days. When at least batch_size (5) old files exist,
        bundles them into a zip named from_DD_MM_YYYY_to_DD_MM_YYYY_alfred_latency_log.zip
        and removes the original individual files.
        """
        if not os.path.exists(LATENCY_DIR):
            return []

        now = datetime.now()
        cutoff_date = now - timedelta(days=min_age_days)
        old_files = []

        for item in os.listdir(LATENCY_DIR):
            # Only target daily log / compressed daily log files (skip existing .zip archives)
            if item.endswith(".zip") or item.endswith(".svg"):
                continue

            date_str = None
            if item.endswith(".log.compressed_logs"):
                date_str = item[:-20]
            elif item.endswith(".log"):
                date_str = item[:-4]

            if not date_str:
                continue

            try:
                f_date = datetime.strptime(date_str, "%Y-%m-%d")
                if f_date < cutoff_date:
                    full_p = os.path.join(LATENCY_DIR, item)
                    old_files.append({"date": f_date, "path": full_p, "name": item})
            except ValueError:
                continue

        # Sort chronologically (oldest to newest)
        old_files.sort(key=lambda x: x["date"])

        created_zips = []
        with self._file_lock:
            # Batch into groups of 5
            while len(old_files) >= batch_size:
                batch = old_files[:batch_size]
                old_files = old_files[batch_size:]

                start_str = batch[0]["date"].strftime("%d_%m_%Y")
                end_str = batch[-1]["date"].strftime("%d_%m_%Y")
                zip_name = f"from_{start_str}_to_{end_str}_alfred_latency_log.zip"
                zip_path = os.path.join(LATENCY_DIR, zip_name)

                try:
                    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        for f_info in batch:
                            zf.write(f_info["path"], arcname=f_info["name"])

                    # Purge source files after successful zip creation
                    for f_info in batch:
                        try:
                            if os.path.exists(f_info["path"]):
                                os.remove(f_info["path"])
                        except Exception:
                            pass

                    created_zips.append(zip_name)
                except Exception:
                    pass

        return created_zips

    # ── Legacy Migration Helper ───────────────────────────────────────────

    def migrate_legacy_records(self) -> int:
        """
        Migrates all existing latency files from old function-based format
        to the new dual-length bucketed format and deletes the old uncompressed/legacy ones.
        """
        if not os.path.exists(LATENCY_DIR):
            return 0

        migrated_count = 0
        with self._file_lock:
            for item in os.listdir(LATENCY_DIR):
                if item.endswith(".zip") or item.endswith(".svg"):
                    continue

                full_p = os.path.join(LATENCY_DIR, item)
                date_str = None
                raw_text = None

                if item.endswith(".log.compressed_logs"):
                    date_str = item[:-20]
                    raw_text = read_compressed_log(full_p)
                elif item.endswith(".log"):
                    date_str = item[:-4]
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                            raw_text = f.read()
                    except Exception:
                        continue

                if not raw_text or not date_str:
                    continue

                # Check if already migrated
                if "# ALFRED LATENCY LOG — CONTENT-LENGTH GROUPED" in raw_text:
                    continue

                grouped = defaultdict(list)
                for line in raw_text.splitlines():
                    line_s = line.strip()
                    if not line_s or line_s.startswith("SUMMARY:") or line_s.startswith("#"):
                        continue
                    parts = [p.strip() for p in line_s.split(",")]
                    if len(parts) >= 5:
                        source = parts[0]
                        try:
                            ql = int(parts[1])
                        except ValueError:
                            ql = 0
                        req_dt = parts[2]
                        out_dt = parts[3]
                        dur_s = parts[4].rstrip("s")
                        try:
                            dur = float(dur_s)
                        except ValueError:
                            dur = 0.0

                        resp_len = ql
                        bucket = get_content_bucket(resp_len)
                        reconstructed = f"{source}, {ql}, {resp_len}, {req_dt}, {out_dt}, {dur:.5f}s, {bucket}"
                        grouped[bucket].append({
                            "line": reconstructed,
                            "query_length": ql,
                            "response_length": resp_len,
                            "duration": dur
                        })

                if not grouped:
                    continue

                # Write migrated log file
                uncompressed_path = os.path.join(LATENCY_DIR, f"{date_str}.log")
                with open(uncompressed_path, "w", encoding="utf-8") as f:
                    f.write("# ALFRED LATENCY LOG — CONTENT-LENGTH GROUPED\n")
                    f.write("# Format: source, query_length, response_length, query_received_at, output_at, duration, bucket\n\n")

                    for b_name, _, _ in BUCKETS:
                        items = grouped.get(b_name, [])
                        if not items:
                            continue
                        f.write(f"=== BUCKET: {b_name} ({len(items)} records) ===\n")
                        for it in items:
                            f.write(it["line"] + "\n")

                        total = len(items)
                        avg_q = sum(it["query_length"] for it in items) / total
                        avg_r = sum(it["response_length"] for it in items) / total
                        durations = [it["duration"] for it in items]
                        avg_d = sum(durations) / total
                        min_d = min(durations)
                        max_d = max(durations)
                        f.write(f"SUMMARY: {b_name}, count={total}, avg_q_len={avg_q:.1f}, "
                                f"avg_resp_len={avg_r:.1f}, avg_dur={avg_d:.5f}s, "
                                f"min_dur={min_d:.5f}s, max_dur={max_d:.5f}s\n\n")

                # Remove old compressed file if existed
                if item.endswith(".compressed_logs") and os.path.exists(full_p):
                    try:
                        os.remove(full_p)
                    except Exception:
                        pass

                # Compress migrated log
                compress_log(uncompressed_path, force=True)
                migrated_count += 1

        return migrated_count

    # ── Cleanup ───────────────────────────────────────────────────────────

    def cleanup_old(self, days: int = RETENTION_DAYS) -> int:
        """Deletes standalone records older than days."""
        if not os.path.exists(LATENCY_DIR):
            return 0

        cutoff = time.time() - (days * 86400)
        deleted = 0
        with self._file_lock:
            for item in os.listdir(LATENCY_DIR):
                if item.endswith(".log") or item.endswith(".compressed_logs"):
                    full_p = os.path.join(LATENCY_DIR, item)
                    try:
                        if os.path.getmtime(full_p) < cutoff:
                            os.remove(full_p)
                            deleted += 1
                    except Exception:
                        pass
        return deleted

    def get_available_dates(self) -> list[dict]:
        """Returns metadata for all available recorded dates and zip archives."""
        if not os.path.exists(LATENCY_DIR):
            return []

        date_files = {}
        for item in os.listdir(LATENCY_DIR):
            full = os.path.join(LATENCY_DIR, item)
            if item.endswith(".log"):
                d = item[:-4]
                date_files[d] = {
                    "date": d,
                    "status": "Active (Uncompressed)",
                    "size_bytes": os.path.getsize(full),
                    "path": full
                }
            elif item.endswith(".log.compressed_logs"):
                d = item[:-20]
                if d not in date_files:
                    date_files[d] = {
                        "date": d,
                        "status": "Archived (Compressed)",
                        "size_bytes": os.path.getsize(full),
                        "path": full
                    }
            elif item.endswith(".zip"):
                date_files[item] = {
                    "date": item,
                    "status": "Batch Zip Archive",
                    "size_bytes": os.path.getsize(full),
                    "path": full
                }

        return sorted(date_files.values(), key=lambda x: x["date"], reverse=True)


# ─── Decorator (Backward Compatibility) ───────────────────────────────────────

def track_latency(source: str = None):
    """
    Lightweight pass-through decorator for backwards compatibility.
    Tracks execution time and returns result without blocking.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            q_len = 0
            for a in args:
                if isinstance(a, str):
                    q_len = len(a)
                    break
            t0 = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                t1 = time.time()
                resp_len = len(result) if isinstance(result, str) else q_len
                label = source or f"{func.__module__}.{func.__qualname__}"
                try:
                    LatencyRecorder().record(
                        source=label,
                        query_length=q_len,
                        response_length=resp_len,
                        query_received_at=t0,
                        output_at=t1
                    )
                except Exception:
                    pass
        return wrapper
    return decorator


# ─── CLI Handlers ─────────────────────────────────────────────────────────────

def _cli_recent():
    """Shows the last 10 queries and comparative latency analysis."""
    recorder = LatencyRecorder()
    comp = recorder.get_recent_comparisons(limit=10)

    if "error" in comp:
        print(f"\n  [!] {comp['error']}\n")
        return

    newest = comp["newest"]
    print("\n╔════════════════════════════════════════════════════════════════════════════════════╗")
    print("║                     ALFRED LATENCY RECENT COMPARISON REPORT                        ║")
    print("╠════════════════════════════════════════════════════════════════════════════════════╣")
    print(f"║  Latest Query Latency  : {newest['duration']:.4f}s ({newest['bucket']})                       ║")
    print(f"║  Latest Content Sizes  : Query={newest['query_length']} chars, Response={newest['response_length']} chars                ║")
    print(f"║  Rolling 10-Avg Latency: {comp['avg_previous_10']:.4f}s                                            ║")

    delta = comp["delta_percent_vs_avg"]
    direction = "slower" if delta > 0 else "faster"
    color = "\033[91m" if delta > 0 else "\033[92m"
    print(f"║  Comparison vs Avg     : {color}{abs(delta):.1f}% {direction}\033[0m                                          ║")

    delta_b = comp["delta_percent_vs_bucket"]
    b_dir = "slower" if delta_b > 0 else "faster"
    print(f"║  Comparison vs Bucket  : {abs(delta_b):.1f}% {b_dir} (Bucket Avg: {comp['same_bucket_avg']:.4f}s)              ║")
    print("╠════════════════════════════════════════════════════════════════════════════════════╣")
    print("║  PREVIOUS 10 RECORDED LATENCIES:                                                   ║")
    print(f"║  {'Timestamp':<23} {'Query':<7} {'Resp':<7} {'Duration':<11} {'Bucket':<15}      ║")
    print("╟────────────────────────────────────────────────────────────────────────────────────╢")

    for r in comp["previous_10"]:
        ts = r["req_dt"][:19]
        print(f"║  {ts:<23} {r['query_length']:<7} {r['response_length']:<7} {r['duration']:<11.4f}s {r['bucket']:<15}      ║")

    print("╚════════════════════════════════════════════════════════════════════════════════════╝\n")


def _cli_show(date_str: str, lines_limit: int = 50):
    recorder = LatencyRecorder()
    lines = recorder.read_records(date_str)
    if not lines:
        print(f"\n  [!] No latency logs found for date '{date_str}'.\n")
        return

    print(f"\n--- ALFRED LATENCY LOG: {date_str} ---")
    displayed = lines[:lines_limit] if lines_limit > 0 else lines
    for l in displayed:
        if l.startswith("SUMMARY:"):
            print(f"\033[92m{l}\033[0m")
        elif l.startswith("==="):
            print(f"\033[94m{l}\033[0m")
        else:
            print(f"  {l}")

    remaining = len(lines) - len(displayed)
    if remaining > 0:
        print(f"\n  ... ({remaining} more lines omitted. Use --lines {len(lines)} to show all)")
    print(f"\n  Total lines: {len(lines)}\n")


def _cli_list():
    recorder = LatencyRecorder()
    dates = recorder.get_available_dates()
    print("\n╔════════════════════════════════════════════════════════════════════════════════════╗")
    print("║                           ALFRED LATENCY LOG ARCHIVES                              ║")
    print("╠════════════════════════════════════════════════════════════════════════════════════╣")
    if not dates:
        print("║   No latency logs recorded yet.                                                    ║")
        print("╚════════════════════════════════════════════════════════════════════════════════════╝\n")
        return

    print(f"║  {'Date / Archive Name':<42} {'Status':<22} {'Size':<10} ║")
    print("╟────────────────────────────────────────────────────────────────────────────────────╢")
    for d in dates:
        size_kb = f"{d['size_bytes'] / 1024:.2f} KB"
        print(f"║  {d['date']:<42} {d['status']:<22} {size_kb:<10} ║")
    print("╚════════════════════════════════════════════════════════════════════════════════════╝\n")


def _cli_archive():
    recorder = LatencyRecorder()
    created = recorder.archive_old_batches(min_age_days=7, batch_size=5)
    if created:
        print(f"\n  Created {len(created)} batch zip archive(s):")
        for z in created:
            print(f"    - {z}")
        print()
    else:
        print("\n  No eligible files found to archive (requires >=5 files older than 7 days).\n")


def _cli_migrate():
    recorder = LatencyRecorder()
    count = recorder.migrate_legacy_records()
    print(f"\n  Migrated {count} legacy latency log files to new content-length grouped schema.\n")


def _cli_help():
    print("""
ALFRED LATENCY RECORDER CLI
Usage: python .\\FILES\\LATENCY_RECORDER.py [options]

Options:
  --recent               Show last 10 latencies with comparative delta metrics
  --stats, --graph       Show visual ASCII/Unicode latency charts & export PNG/SVG
  --png                  Generate high-res PNG graphs (Line, Box, Scatter, Dashboard)
  --type <type>          Graph type for --png: line, box, scatter, dashboard, all (default: all)
  --plot                 Open interactive Tkinter canvas graph window
  --show <date>          Display records and bucket summaries for YYYY-MM-DD
  --archive              Run batch zip compression (>7 days old in groups of 5)
  --migrate              Migrate all old latency logs to new content-length schema
  --list                 List all available daily archives and zip bundles
  --clean                Delete records older than retention period (15 days)
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--recent", action="store_true", help="Show recent 10 latencies with comparison")
    parser.add_argument("--stats", "--graph", action="store_true", dest="stats", help="Show graphical stats")
    parser.add_argument("--png", action="store_true", help="Generate high-res PNG graphs")
    parser.add_argument("--type", type=str, default="all", help="Graph type for --png: line, box, scatter, dashboard, all")
    parser.add_argument("--plot", action="store_true", help="Open Tkinter plot window")
    parser.add_argument("--archive", action="store_true", help="Batch zip files older than 7 days")
    parser.add_argument("--migrate", action="store_true", help="Migrate legacy latency logs")
    parser.add_argument("--show", type=str, default=None, help="Inspect date YYYY-MM-DD")
    parser.add_argument("--lines", type=int, default=50, help="Max lines to display")
    parser.add_argument("--list", action="store_true", help="List all dates and archives")
    parser.add_argument("--clean", action="store_true", help="Clean old records")
    parser.add_argument("--help", "-h", action="store_true", help="Show help")

    args, _ = parser.parse_known_args()

    if args.help:
        _cli_help()
    elif args.recent:
        _cli_recent()
    elif args.stats:
        recorder = LatencyRecorder()
        recorder.show_graphical_stats(mode="cli")
        png_out = recorder.generate_png_graphs(graph_type="all")
        if png_out:
            print("  Exported high-res PNG graphs:")
            for k, p in png_out.items():
                print(f"    -> [{k.upper()}]: {p}")
            print()
    elif args.png:
        print(f"\n  Generating latency PNG graphs (type: {args.type})...")
        outputs = LatencyRecorder().generate_png_graphs(graph_type=args.type)
        if outputs:
            print(f"  Successfully generated {len(outputs)} graph(s):")
            for k, p in outputs.items():
                print(f"    - [{k.upper()}]: {p}")
            print()
        else:
            print("  [!] Failed to generate PNG graphs.\n")
    elif args.plot:
        LatencyRecorder().show_graphical_stats(mode="gui")
    elif args.archive:
        _cli_archive()
    elif args.migrate:
        _cli_migrate()
    elif args.list:
        _cli_list()
    elif args.clean:
        del_count = LatencyRecorder().cleanup_old(RETENTION_DAYS)
        print(f"\n  Cleaned up {del_count} old files.\n")
    elif args.show:
        _cli_show(args.show, lines_limit=args.lines)
    else:
        _cli_help()
