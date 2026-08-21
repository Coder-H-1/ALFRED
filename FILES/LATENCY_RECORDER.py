"""
LATENCY_RECORDER.py — Performance latency tracker for ALFRED.

Records per-call latency data into a SQLite database (logs/latency/latency.db).
Provides:
    - LatencyRecorder class with thread-safe recording
    - @track_latency decorator for auto-instrumentation
    - Background daemon thread for periodic reorganisation
    - CLI interface: --list, --show <source>, --clean, --help

Usage (standalone):
    python .\\FILES\\LATENCY_RECORDER.py              # help
    python .\\FILES\\LATENCY_RECORDER.py --list        # overview report
    python .\\FILES\\LATENCY_RECORDER.py --show <src>  # per-function summary
    python .\\FILES\\LATENCY_RECORDER.py --clean       # force cleanup of old records
"""

import os
import sys
import time
import sqlite3
import threading
import functools
import argparse
from datetime import datetime, timedelta


# ─── Paths ───────────────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATENCY_DIR = os.path.join(_BASE_DIR, "logs", "latency")
DB_PATH = os.path.join(LATENCY_DIR, "latency.db")

RETENTION_DAYS = 15


# ─── LatencyRecorder ─────────────────────────────────────────────────────────

class LatencyRecorder:
    """Thread-safe SQLite-backed latency recorder."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton — only one recorder per process."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, auto_reorganize: bool = True):
        if getattr(self, "_initialized", False):
            return
        self._db_lock = threading.Lock()
        os.makedirs(LATENCY_DIR, exist_ok=True)
        self._init_db()
        self._initialized = True

        if auto_reorganize:
            self._start_reorganizer()

    # ── Database Setup ────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Create a new connection for the calling thread."""
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS records (
                        id              INTEGER PRIMARY KEY AUTOINCREMENT,
                        source          TEXT    NOT NULL,
                        timestamp       TEXT    NOT NULL,
                        query_length    INTEGER DEFAULT 0,
                        query_received  REAL    NOT NULL,
                        output_at       REAL    NOT NULL,
                        time_taken_ms   REAL    NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_records_source    ON records(source);
                    CREATE INDEX IF NOT EXISTS idx_records_timestamp ON records(timestamp);

                    CREATE TABLE IF NOT EXISTS summaries (
                        source           TEXT PRIMARY KEY,
                        call_count       INTEGER DEFAULT 0,
                        avg_time_ms      REAL    DEFAULT 0.0,
                        avg_query_length REAL    DEFAULT 0.0,
                        min_time_ms      REAL    DEFAULT 0.0,
                        max_time_ms      REAL    DEFAULT 0.0,
                        last_updated     TEXT    NOT NULL
                    );
                """)
                conn.commit()
            finally:
                conn.close()

    # ── Core Recording ────────────────────────────────────────────────────

    def record(self, source: str, query_length: int,
               query_received_at: float, output_at: float):
        """Insert one latency record."""
        time_taken_ms = (output_at - query_received_at) * 1000.0
        ts = datetime.now().isoformat(timespec="milliseconds")

        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """INSERT INTO records
                       (source, timestamp, query_length, query_received, output_at, time_taken_ms)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (source, ts, query_length, query_received_at, output_at, time_taken_ms)
                )
                conn.commit()
            finally:
                conn.close()

    def startup_record(self):
        """Write a sentinel record marking program startup."""
        now = time.time()
        self.record(
            source="SYSTEM.STARTUP",
            query_length=0,
            query_received_at=now,
            output_at=now
        )

    # ── Cleanup ───────────────────────────────────────────────────────────

    def cleanup_old(self, days: int = RETENTION_DAYS) -> int:
        """Delete records older than `days`. Returns count deleted."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._db_lock:
            conn = self._get_conn()
            try:
                cur = conn.execute(
                    "DELETE FROM records WHERE timestamp < ?", (cutoff,)
                )
                deleted = cur.rowcount
                conn.commit()
                return deleted
            finally:
                conn.close()

    # ── Reorganizer (background thread) ───────────────────────────────────

    def _start_reorganizer(self):
        """Spawn a daemon thread that reorganizes on startup then every hour."""
        t = threading.Thread(target=self._reorganizer_loop, daemon=True)
        t.start()

    def _reorganizer_loop(self):
        """Background loop: reorganize + cleanup, then sleep 1 hour."""
        try:
            # Initial run on startup
            self.cleanup_old()
            self.reorganize()
        except Exception:
            pass

        while True:
            try:
                time.sleep(3600)  # every hour
                self.cleanup_old()
                self.reorganize()
            except Exception:
                pass

    def reorganize(self):
        """Aggregate records into summaries table, grouped by source."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                rows = conn.execute("""
                    SELECT source,
                           COUNT(*)          AS call_count,
                           AVG(time_taken_ms) AS avg_time,
                           AVG(query_length)  AS avg_qlen,
                           MIN(time_taken_ms) AS min_time,
                           MAX(time_taken_ms) AS max_time
                    FROM records
                    WHERE source != 'SYSTEM.STARTUP'
                    GROUP BY source
                """).fetchall()

                now = datetime.now().isoformat(timespec="seconds")
                for row in rows:
                    conn.execute(
                        """INSERT OR REPLACE INTO summaries
                           (source, call_count, avg_time_ms, avg_query_length,
                            min_time_ms, max_time_ms, last_updated)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (row[0], row[1], row[2], row[3], row[4], row[5], now)
                    )
                conn.commit()
            finally:
                conn.close()

    # ── Query Methods ─────────────────────────────────────────────────────

    def get_summary(self, source: str = None) -> list[dict]:
        """Return aggregated stats. If source given, filter by it."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                if source:
                    rows = conn.execute(
                        "SELECT * FROM summaries WHERE source LIKE ?",
                        (f"%{source}%",)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM summaries ORDER BY call_count DESC"
                    ).fetchall()

                return [
                    {
                        "source": r[0], "call_count": r[1],
                        "avg_time_ms": round(r[2], 2),
                        "avg_query_length": round(r[3], 1),
                        "min_time_ms": round(r[4], 2),
                        "max_time_ms": round(r[5], 2),
                        "last_updated": r[6]
                    }
                    for r in rows
                ]
            finally:
                conn.close()

    def get_record_stats(self) -> dict:
        """Return total record count, date range, and recent sessions."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                total = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
                date_range = conn.execute(
                    "SELECT MIN(timestamp), MAX(timestamp) FROM records"
                ).fetchone()

                # Recent 3 "sessions" = distinct dates based on startup records
                sessions_raw = conn.execute("""
                    SELECT DATE(timestamp) AS day, COUNT(*) AS cnt
                    FROM records
                    GROUP BY DATE(timestamp)
                    ORDER BY day DESC
                    LIMIT 3
                """).fetchall()

                sessions = [
                    {"date": s[0], "record_count": s[1]}
                    for s in sessions_raw
                ]

                return {
                    "total_records": total,
                    "earliest": date_range[0] if date_range else None,
                    "latest": date_range[1] if date_range else None,
                    "recent_sessions": sessions
                }
            finally:
                conn.close()


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
                    recorder = LatencyRecorder(auto_reorganize=False)
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

def _cli_list():
    """--list: overview report."""
    recorder = LatencyRecorder(auto_reorganize=False)
    stats = recorder.get_record_stats()

    print("\n╔══════════════════════════════════════════╗")
    print("║       ALFRED  LATENCY  REPORT            ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Total Records : {stats['total_records']:<23} ║")
    print(f"║  Date Range    : {(stats['earliest'] or 'N/A')[:10]} → {(stats['latest'] or 'N/A')[:10]}  ║")
    print("╠══════════════════════════════════════════╣")
    print("║  Recent Sessions (by date)               ║")
    print("╟──────────────────────────────────────────╢")

    if stats["recent_sessions"]:
        for s in stats["recent_sessions"]:
            print(f"║   {s['date']}  —  {s['record_count']:>5} records         ║")
    else:
        print("║   No sessions recorded yet.              ║")

    print("╚══════════════════════════════════════════╝\n")


def _cli_show(source: str):
    """--show <source>: per-function summary."""
    recorder = LatencyRecorder(auto_reorganize=False)
    # Force fresh reorganize before showing
    recorder.reorganize()
    summaries = recorder.get_summary(source)

    if not summaries:
        print(f"\n  No summary data found for '{source}'.\n")
        return

    print(f"\n{'Source':<40} {'Calls':>6} {'Average seconds':>15} {'Min seconds':>15} {'Max seconds':>15} {'Avg QLen':>9}")
    print("─" * 105)
    for s in summaries:
        print(
            f"{s['source']:<40} {s['call_count']:>6} "
            f"{s['avg_time_ms']/1000:>15.5f} {s['min_time_ms']/1000:>15.5f} "
            f"{s['max_time_ms']/1000:>15.5f} {s['avg_query_length']:>9.1f}"
        )
    print()


def _cli_clean():
    """--clean: force cleanup."""
    recorder = LatencyRecorder(auto_reorganize=False)
    deleted = recorder.cleanup_old()
    print(f"\n  Cleaned up {deleted} records older than {RETENTION_DAYS} days.\n")


def _cli_help():
    print("""
╔══════════════════════════════════════════════════════════════╗
║               ALFRED  LATENCY  RECORDER  CLI                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Usage:                                                      ║
║    python .\\FILES\\LATENCY_RECORDER.py [command]              ║
║                                                              ║
║  Commands:                                                   ║
║    --list          Show total records, recent 3 sessions     ║
║                    with per-date record counts.              ║
║                                                              ║
║    --show <source> Show per-function summary stats.          ║
║                    <source> can be partial match.            ║
║                    e.g. --show commands                      ║
║                                                              ║
║    --clean         Force cleanup of records older than       ║
║                    15 days.                                   ║
║                                                              ║
║    (no arguments)  Show this help message.                   ║
║                                                              ║
║  Record Storage:                                             ║
║    Database : logs/latency/latency.db                        ║
║    Retention: 15 days (auto-cleaned by background thread)    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--show", type=str, default=None)
    parser.add_argument("--clean", action="store_true")

    args, _ = parser.parse_known_args()

    if args.list:
        _cli_list()
    elif args.show:
        _cli_show(args.show)
    elif args.clean:
        _cli_clean()
    else:
        _cli_help()
