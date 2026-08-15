"""
long_term_memory.py — Production-grade persistent memory for ALFRED.

Works standalone (CLI) or embedded (ALFRED runtime).
Zero external dependencies — stdlib only (sqlite3, datetime, uuid, argparse, json, csv, os, re).

CLI Usage:
    python -m FILES.long_term_memory --help
    python -m FILES.long_term_memory search "president"
    python -m FILES.long_term_memory date 2026-04-07
    python -m FILES.long_term_memory print --last 20
    python -m FILES.long_term_memory delete --id 42
    python -m FILES.long_term_memory relations --id 15
    python -m FILES.long_term_memory sessions
    python -m FILES.long_term_memory export --format json
"""

import sqlite3
import datetime
import uuid
import argparse
import json
import csv
import os
import re
import io
import sys


# ──────────────────────────────────────────────────────────────────────
# Auto-Tagging: Extract meaningful keywords from text
# ──────────────────────────────────────────────────────────────────────

# Common English stop words to filter out
_STOP_WORDS = frozenset({
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you",
    "your", "yours", "yourself", "yourselves", "he", "him", "his",
    "himself", "she", "her", "hers", "herself", "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves", "what", "which",
    "who", "whom", "this", "that", "these", "those", "am", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if",
    "or", "because", "as", "until", "while", "of", "at", "by", "for",
    "with", "about", "against", "between", "through", "during", "before",
    "after", "above", "below", "to", "from", "up", "down", "in", "out",
    "on", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "s", "t",
    "can", "will", "just", "don", "should", "now", "d", "ll", "m", "o",
    "re", "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn",
    "hasn", "haven", "isn", "ma", "mightn", "mustn", "needn", "shan",
    "shouldn", "wasn", "weren", "won", "wouldn", "sir", "please",
    "could", "would", "shall", "may", "might", "must", "tell", "know",
    "want", "need", "like", "think", "say", "said", "get", "go", "make",
    "come", "take", "see", "look", "give", "find", "let", "put", "also",
    "well", "back", "much", "even", "still", "way", "good", "new",
    "right", "thank", "thanks", "okay", "ok", "yes", "yeah", "hey",
    "hello", "hi", "help", "something", "anything", "everything",
    "nothing", "someone", "anyone", "everyone", "thing", "things",
    "alfred", "butler", "user", "open", "close", "start", "stop",
})


def _auto_tag(content: str, max_tags: int = 8) -> str:
    """
    Extract meaningful keywords from content for tagging.
    Returns comma-separated lowercase tags. 
    Keeps only words >= 3 chars that aren't stop words.
    """
    if not content:
        return ""

    # Lowercase and extract words (alphanumeric only)
    words = re.findall(r'[a-zA-Z]{3,}', content.lower())

    # Filter stop words and deduplicate preserving order
    seen = set()
    tags = []
    for w in words:
        if w not in _STOP_WORDS and w not in seen:
            seen.add(w)
            tags.append(w)
            if len(tags) >= max_tags:
                break

    return ",".join(tags)


# ──────────────────────────────────────────────────────────────────────
# Default DB path (relative to this file's directory)
# ──────────────────────────────────────────────────────────────────────

_DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Mem")
_DEFAULT_DB_PATH = os.path.join(_DEFAULT_DB_DIR, "alfred_memory.db")


# ──────────────────────────────────────────────────────────────────────
# LongTermMemory Class
# ──────────────────────────────────────────────────────────────────────

class LongTermMemory:
    """
    Production-grade persistent memory for ALFRED.
    
    Works standalone (CLI) or embedded (ALFRED runtime).
    All data stored in SQLite with FTS5 for full-text search.
    Every entry timestamped with ISO 8601 datetime.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize memory system. Creates DB + tables if they don't exist.
        
        Args:
            db_path: Path to SQLite database. Defaults to FILES/Mem/alfred_memory.db
        """
        self.db_path = db_path or _DEFAULT_DB_PATH

        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row  # dict-like access
        self._conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
        self._conn.execute("PRAGMA foreign_keys=ON")
        
        self._ensure_tables()
        self._current_session_id: str = None

    # ── Internal Helpers ─────────────────────────────────────────────

    def _ensure_tables(self):
        """Create all tables and indexes if they don't exist."""
        cur = self._conn.cursor()

        cur.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id  TEXT PRIMARY KEY,
                started_at  TEXT NOT NULL,
                ended_at    TEXT DEFAULT NULL,
                summary     TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS memories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('user','alfred')),
                content     TEXT    NOT NULL,
                tags        TEXT    DEFAULT '',
                parent_id   INTEGER DEFAULT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (parent_id) REFERENCES memories(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_memories_session 
                ON memories(session_id);
            CREATE INDEX IF NOT EXISTS idx_memories_timestamp 
                ON memories(timestamp);
            CREATE INDEX IF NOT EXISTS idx_memories_role 
                ON memories(role);
            CREATE INDEX IF NOT EXISTS idx_memories_parent 
                ON memories(parent_id);
        """)

        # FTS5 virtual table — check if it exists first
        fts_exists = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_fts'"
        ).fetchone()

        if not fts_exists:
            cur.execute("""
                CREATE VIRTUAL TABLE memory_fts USING fts5(
                    content,
                    tags,
                    content=memories,
                    content_rowid=id
                )
            """)
            # Populate FTS from any existing data (safety for upgrades)
            cur.execute("""
                INSERT INTO memory_fts(rowid, content, tags)
                SELECT id, content, tags FROM memories
            """)

        self._conn.commit()

    @staticmethod
    def _now() -> str:
        """Returns current timestamp in ISO 8601 format with timezone."""
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
        return now.isoformat()

    def _sync_fts_insert(self, rowid: int, content: str, tags: str):
        """Keep FTS5 index in sync after INSERT."""
        self._conn.execute(
            "INSERT INTO memory_fts(rowid, content, tags) VALUES (?, ?, ?)",
            (rowid, content, tags)
        )

    def _sync_fts_delete(self, rowid: int, content: str, tags: str):
        """Keep FTS5 index in sync before DELETE."""
        self._conn.execute(
            "INSERT INTO memory_fts(memory_fts, rowid, content, tags) VALUES ('delete', ?, ?, ?)",
            (rowid, content, tags)
        )

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a sqlite3.Row to a plain dict."""
        if row is None:
            return None
        return dict(row)

    # ── Session Management ───────────────────────────────────────────

    def start_session(self) -> str:
        """
        Start a new memory session. Call when ALFRED boots.
        
        Returns:
            session_id (str): UUID of the new session.
        """
        self._current_session_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO sessions (session_id, started_at) VALUES (?, ?)",
            (self._current_session_id, self._now())
        )
        self._conn.commit()
        return self._current_session_id

    def end_session(self, summary: str = "") -> None:
        """
        End the current session. Call when ALFRED shuts down.
        
        Args:
            summary: Optional 1-line summary of the session.
        """
        if not self._current_session_id:
            return

        self._conn.execute(
            "UPDATE sessions SET ended_at = ?, summary = ? WHERE session_id = ?",
            (self._now(), summary, self._current_session_id)
        )
        self._conn.commit()
        self._current_session_id = None

    def get_current_session_id(self) -> str:
        """Returns the current active session ID, or None."""
        return self._current_session_id

    # ── Add Memories ─────────────────────────────────────────────────

    def add(self, role: str, content: str, tags: str = "", parent_id: int = None) -> int:
        """
        Store one memory entry with automatic timestamp.
        
        Args:
            role: 'user' or 'alfred'
            content: The text content of the memory
            tags: Comma-separated tags (auto-generated if empty)
            parent_id: Links this memory to a parent (for reply chains)
            
        Returns:
            id (int): The ID of the newly inserted memory.
        """
        if role not in ('user', 'alfred'):
            raise ValueError(f"role must be 'user' or 'alfred', got '{role}'")

        # Use current session or create an ad-hoc one
        session_id = self._current_session_id
        if not session_id:
            session_id = "cli-" + str(uuid.uuid4())[:8]
            # Ensure ad-hoc session exists
            existing = self._conn.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()
            if not existing:
                self._conn.execute(
                    "INSERT INTO sessions (session_id, started_at) VALUES (?, ?)",
                    (session_id, self._now())
                )

        # Auto-tag if no tags provided
        if not tags.strip():
            tags = _auto_tag(content)

        timestamp = self._now()

        cur = self._conn.execute(
            """INSERT INTO memories (session_id, timestamp, role, content, tags, parent_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, timestamp, role, content, tags, parent_id)
        )
        rowid = cur.lastrowid

        # Sync FTS
        self._sync_fts_insert(rowid, content, tags)
        self._conn.commit()

        return rowid

    def add_exchange(self, user_query: str, alfred_reply: str, tags: str = "") -> tuple:
        """
        Convenience: stores user query + alfred reply as linked pair.
        
        Args:
            user_query: What the user said
            alfred_reply: What ALFRED responded
            tags: Optional tags (auto-generated for both if empty)
            
        Returns:
            (user_id, alfred_id): IDs of both inserted memories.
        """
        user_tags = tags if tags else _auto_tag(user_query)
        alfred_tags = tags if tags else _auto_tag(alfred_reply)

        user_id = self.add(role="user", content=user_query, tags=user_tags)
        alfred_id = self.add(role="alfred", content=alfred_reply, tags=alfred_tags, parent_id=user_id)

        return (user_id, alfred_id)

    # ── Delete Memories ──────────────────────────────────────────────

    def delete(self, memory_id: int) -> bool:
        """
        Delete a specific memory by ID.
        
        Args:
            memory_id: The ID of the memory to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        # Fetch content first for FTS cleanup
        row = self._conn.execute(
            "SELECT id, content, tags FROM memories WHERE id = ?",
            (memory_id,)
        ).fetchone()

        if not row:
            return False

        # Remove from FTS first
        self._sync_fts_delete(row['id'], row['content'], row['tags'])

        # Remove the memory
        self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._conn.commit()
        return True

    def delete_session(self, session_id: str) -> int:
        """
        Delete all memories from a specific session.
        
        Args:
            session_id: The session UUID to delete.
            
        Returns:
            Number of memories deleted.
        """
        # Get all rows for FTS cleanup
        rows = self._conn.execute(
            "SELECT id, content, tags FROM memories WHERE session_id = ?",
            (session_id,)
        ).fetchall()

        # Remove from FTS
        for row in rows:
            self._sync_fts_delete(row['id'], row['content'], row['tags'])

        # Delete memories
        self._conn.execute("DELETE FROM memories WHERE session_id = ?", (session_id,))
        # Delete session record
        self._conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        self._conn.commit()

        return len(rows)

    # ── Search ───────────────────────────────────────────────────────

    def search(self, keyword: str, limit: int = 50) -> list:
        """
        Full-text search across all memories using FTS5.
        
        Args:
            keyword: Search term (supports FTS5 query syntax).
            limit: Max results to return.
            
        Returns:
            List of matching memory dicts.
        """
        # Escape special FTS characters for safety
        safe_keyword = keyword.replace('"', '""')

        rows = self._conn.execute(
            """SELECT m.id, m.session_id, m.timestamp, m.role, m.content, m.tags, m.parent_id
               FROM memories m
               JOIN memory_fts f ON m.id = f.rowid
               WHERE memory_fts MATCH ?
               ORDER BY m.timestamp DESC
               LIMIT ?""",
            (f'"{safe_keyword}"', limit)
        ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def search_by_date(self, start_date: str, end_date: str = None) -> list:
        """
        Find memories within a date or date range.
        
        Args:
            start_date: Date string "YYYY-MM-DD"
            end_date: Optional end date "YYYY-MM-DD". If None, searches single day.
            
        Returns:
            List of matching memory dicts.
        """
        if end_date is None:
            end_date = start_date

        # Build ISO range: start of start_date to end of end_date
        start_iso = f"{start_date}T00:00:00"
        end_iso = f"{end_date}T23:59:59"

        rows = self._conn.execute(
            """SELECT id, session_id, timestamp, role, content, tags, parent_id
               FROM memories
               WHERE timestamp >= ? AND timestamp <= ?
               ORDER BY timestamp ASC""",
            (start_iso, end_iso)
        ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    # ── Relations ────────────────────────────────────────────────────

    def get_relations(self, memory_id: int) -> list:
        """
        Get the full conversation chain for a memory.
        Walks up to the root (user query) and down to all replies.
        
        Args:
            memory_id: The memory ID to find relations for.
            
        Returns:
            List of related memory dicts, ordered by timestamp.
        """
        # First, find the root of the chain (walk up parent_id)
        root_id = memory_id
        visited = {root_id}

        while True:
            row = self._conn.execute(
                "SELECT parent_id FROM memories WHERE id = ?", (root_id,)
            ).fetchone()
            if row is None or row['parent_id'] is None:
                break
            root_id = row['parent_id']
            if root_id in visited:
                break  # Safety: prevent infinite loop on corrupted data
            visited.add(root_id)

        # Now collect the root + all descendants
        chain = []

        def _collect(node_id):
            row = self._conn.execute(
                "SELECT id, session_id, timestamp, role, content, tags, parent_id FROM memories WHERE id = ?",
                (node_id,)
            ).fetchone()
            if row:
                chain.append(self._row_to_dict(row))
                # Find children (replies to this memory)
                children = self._conn.execute(
                    "SELECT id FROM memories WHERE parent_id = ? ORDER BY timestamp ASC",
                    (node_id,)
                ).fetchall()
                for child in children:
                    _collect(child['id'])

        _collect(root_id)
        return chain

    # ── Retrieval for Prompt Injection ───────────────────────────────

    def get_recent(self, n: int = 5) -> str:
        """
        Get last N exchanges formatted for LLM prompt injection.
        Replaces the old Memory.get_history() for LTM-backed context.
        
        Args:
            n: Number of exchange pairs to return.
            
        Returns:
            Formatted string: "User: ...\nAlfred: ...\n"
        """
        rows = self._conn.execute(
            """SELECT timestamp, role, content FROM memories
               ORDER BY timestamp DESC
               LIMIT ?""",
            (n * 2,)  # user + alfred = 2 rows per exchange
        ).fetchall()

        if not rows:
            return ""

        # Reverse to chronological order
        rows = list(reversed(rows))

        lines = []
        for row in rows:
            prefix = "User" if row['role'] == 'user' else "Butler"
            lines.append(f"{prefix}: {row['content']}")

        return "\n".join(lines)

    # ── Print / Display ──────────────────────────────────────────────

    def print_memories(self, limit: int = 20, offset: int = 0, session_id: str = None) -> str:
        """
        Pretty-print memories.
        
        Args:
            limit: Max memories to show.
            offset: Skip first N memories.
            session_id: Filter by session (optional).
            
        Returns:
            Formatted string of memories.
        """
        if session_id:
            rows = self._conn.execute(
                """SELECT id, session_id, timestamp, role, content, tags, parent_id
                   FROM memories WHERE session_id = ?
                   ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
                (session_id, limit, offset)
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT id, session_id, timestamp, role, content, tags, parent_id
                   FROM memories
                   ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
                (limit, offset)
            ).fetchall()

        if not rows:
            return "No memories found."

        lines = []
        lines.append(f"{'─' * 80}")
        lines.append(f"  {'ID':<6} {'TIME':<22} {'ROLE':<8} {'CONTENT':<40}")
        lines.append(f"{'─' * 80}")

        for row in reversed(list(rows)):  # Show chronological
            ts = row['timestamp'][:19].replace('T', ' ')
            content = row['content']
            # Truncate long content for display
            if len(content) > 60:
                content = content[:57] + "..."
            role_display = "👤 User" if row['role'] == 'user' else "🤖 ALFRD"
            lines.append(f"  {row['id']:<6} {ts:<22} {role_display:<8} {content}")
            if row['tags']:
                lines.append(f"         {'':22} {'':8} 🏷️  {row['tags']}")

        lines.append(f"{'─' * 80}")
        lines.append(f"  Showing {len(rows)} memories")
        return "\n".join(lines)

    # ── Sessions ─────────────────────────────────────────────────────

    def list_sessions(self) -> list:
        """
        List all recorded sessions with their date ranges.
        
        Returns:
            List of session dicts.
        """
        rows = self._conn.execute(
            """SELECT s.session_id, s.started_at, s.ended_at, s.summary,
                      COUNT(m.id) as memory_count
               FROM sessions s
               LEFT JOIN memories m ON s.session_id = m.session_id
               GROUP BY s.session_id
               ORDER BY s.started_at DESC"""
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ── Export ────────────────────────────────────────────────────────

    def export(self, format: str = "json", filepath: str = None) -> str:
        """
        Export all memories.
        
        Args:
            format: 'json' or 'csv'
            filepath: Output file path. If None, returns string.
            
        Returns:
            The exported data as string (or filepath if written to file).
        """
        rows = self._conn.execute(
            """SELECT id, session_id, timestamp, role, content, tags, parent_id
               FROM memories ORDER BY timestamp ASC"""
        ).fetchall()

        data = [self._row_to_dict(r) for r in rows]

        if format == "json":
            output = json.dumps(data, indent=2, ensure_ascii=False)
        elif format == "csv":
            if not data:
                output = ""
            else:
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                output = buf.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")

        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(output)
            return f"Exported {len(data)} memories to {filepath}"

        return output

    # ── Stats ─────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Get memory statistics."""
        total = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        sessions = self._conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        user_msgs = self._conn.execute("SELECT COUNT(*) FROM memories WHERE role='user'").fetchone()[0]
        alfred_msgs = self._conn.execute("SELECT COUNT(*) FROM memories WHERE role='alfred'").fetchone()[0]
        
        oldest = self._conn.execute("SELECT MIN(timestamp) FROM memories").fetchone()[0]
        newest = self._conn.execute("SELECT MAX(timestamp) FROM memories").fetchone()[0]

        return {
            "total_memories": total,
            "total_sessions": sessions,
            "user_messages": user_msgs,
            "alfred_messages": alfred_msgs,
            "oldest_memory": oldest or "N/A",
            "newest_memory": newest or "N/A",
            "db_size_kb": round(os.path.getsize(self.db_path) / 1024, 1) if os.path.exists(self.db_path) else 0
        }

    # ── Cleanup ───────────────────────────────────────────────────────

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __del__(self):
        self.close()


# ══════════════════════════════════════════════════════════════════════
# CLI Interface
# ══════════════════════════════════════════════════════════════════════

def _print_sessions_table(sessions: list):
    """Pretty-print sessions list."""
    if not sessions:
        print("No sessions recorded.")
        return

    print(f"{'─' * 90}")
    print(f"  {'SESSION ID':<38} {'STARTED':<22} {'ENDED':<22} {'#':<5}")
    print(f"{'─' * 90}")
    for s in sessions:
        started = (s['started_at'] or '')[:19].replace('T', ' ')
        ended = (s['ended_at'] or 'active')[:19].replace('T', ' ')
        summary = s.get('summary', '') or ''
        print(f"  {s['session_id']:<38} {started:<22} {ended:<22} {s['memory_count']:<5}")
        if summary:
            print(f"    📝 {summary}")
    print(f"{'─' * 90}")
    print(f"  Total: {len(sessions)} sessions")


def _print_search_results(results: list, label: str = "Search Results"):
    """Pretty-print search results."""
    if not results:
        print(f"No results found.")
        return

    print(f"\n  🔍 {label} ({len(results)} found)")
    print(f"{'─' * 80}")

    for r in results:
        ts = r['timestamp'][:19].replace('T', ' ')
        role = "👤 User" if r['role'] == 'user' else "🤖 ALFRD"
        content = r['content']
        if len(content) > 70:
            content = content[:67] + "..."
        print(f"  [{r['id']:>4}] {ts}  {role}  {content}")
        if r.get('tags'):
            print(f"         🏷️  {r['tags']}")

    print(f"{'─' * 80}")


def main():
    """CLI entry point for ALFRED Long-Term Memory."""

    parser = argparse.ArgumentParser(
        prog="alfred-memory",
        description="🧠 ALFRED Long-Term Memory — Search, manage, and export conversation history.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s search "president"           Search all memories for "president"
  %(prog)s date 2026-04-07              Show memories from April 7
  %(prog)s date 2026-04-01 2026-04-07   Show memories in date range
  %(prog)s print --last 20              Print recent 20 memories
  %(prog)s print --session abc123       Print memories from session
  %(prog)s delete --id 42               Delete memory #42
  %(prog)s delete --session abc123      Delete entire session
  %(prog)s relations --id 42            Show conversation chain for #42
  %(prog)s sessions                     List all sessions
  %(prog)s stats                        Show memory statistics
  %(prog)s export --format json         Export all as JSON
  %(prog)s add --role user --content "hello"   Add memory manually
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # search
    sp_search = subparsers.add_parser("search", help="Full-text search memories")
    sp_search.add_argument("keyword", type=str, help="Search term")
    sp_search.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")

    # date
    sp_date = subparsers.add_parser("date", help="Search memories by date")
    sp_date.add_argument("start_date", type=str, help="Start date (YYYY-MM-DD)")
    sp_date.add_argument("end_date", type=str, nargs="?", default=None, help="End date (YYYY-MM-DD)")

    # print
    sp_print = subparsers.add_parser("print", help="Print recent memories")
    sp_print.add_argument("--last", type=int, default=20, help="Number of recent memories (default: 20)")
    sp_print.add_argument("--session", type=str, default=None, help="Filter by session ID")

    # delete
    sp_delete = subparsers.add_parser("delete", help="Delete memories")
    sp_delete.add_argument("--id", type=int, default=None, help="Delete specific memory by ID")
    sp_delete.add_argument("--session", type=str, default=None, help="Delete entire session")

    # relations
    sp_rel = subparsers.add_parser("relations", help="Show conversation chain")
    sp_rel.add_argument("--id", type=int, required=True, help="Memory ID to find relations for")

    # sessions
    subparsers.add_parser("sessions", help="List all sessions")

    # stats
    subparsers.add_parser("stats", help="Show memory statistics")

    # export
    sp_export = subparsers.add_parser("export", help="Export memories")
    sp_export.add_argument("--format", type=str, choices=["json", "csv"], default="json", help="Export format")
    sp_export.add_argument("--output", type=str, default=None, help="Output file path")

    # add
    sp_add = subparsers.add_parser("add", help="Add a memory manually")
    sp_add.add_argument("--role", type=str, choices=["user", "alfred"], required=True, help="Role")
    sp_add.add_argument("--content", type=str, required=True, help="Memory content")
    sp_add.add_argument("--tags", type=str, default="", help="Comma-separated tags")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize memory (no model loading, just SQLite)
    ltm = LongTermMemory()

    try:
        if args.command == "search":
            results = ltm.search(args.keyword, limit=args.limit)
            _print_search_results(results, f'Results for "{args.keyword}"')

        elif args.command == "date":
            results = ltm.search_by_date(args.start_date, args.end_date)
            label = f"Memories on {args.start_date}"
            if args.end_date:
                label = f"Memories from {args.start_date} to {args.end_date}"
            _print_search_results(results, label)

        elif args.command == "print":
            output = ltm.print_memories(limit=args.last, session_id=args.session)
            print(output)

        elif args.command == "delete":
            if args.id is not None:
                success = ltm.delete(args.id)
                if success:
                    print(f"✅ Deleted memory #{args.id}")
                else:
                    print(f"❌ Memory #{args.id} not found")
            elif args.session:
                count = ltm.delete_session(args.session)
                print(f"✅ Deleted {count} memories from session {args.session}")
            else:
                print("❌ Specify --id or --session")

        elif args.command == "relations":
            chain = ltm.get_relations(args.id)
            if chain:
                print(f"\n  🔗 Conversation chain for memory #{args.id}")
                print(f"{'─' * 80}")
                for i, r in enumerate(chain):
                    ts = r['timestamp'][:19].replace('T', ' ')
                    role = "👤 User" if r['role'] == 'user' else "🤖 ALFRD"
                    marker = "  ├─" if i < len(chain) - 1 else "  └─"
                    print(f"{marker} [{r['id']:>4}] {ts}  {role}  {r['content']}")
                print(f"{'─' * 80}")
            else:
                print(f"❌ No relations found for memory #{args.id}")

        elif args.command == "sessions":
            sessions = ltm.list_sessions()
            _print_sessions_table(sessions)

        elif args.command == "stats":
            s = ltm.stats()
            print(f"\n  🧠 ALFRED Memory Statistics")
            print(f"{'─' * 40}")
            print(f"  Total Memories  : {s['total_memories']}")
            print(f"  Total Sessions  : {s['total_sessions']}")
            print(f"  User Messages   : {s['user_messages']}")
            print(f"  ALFRED Messages : {s['alfred_messages']}")
            print(f"  Oldest Memory   : {s['oldest_memory']}")
            print(f"  Newest Memory   : {s['newest_memory']}")
            print(f"  DB Size         : {s['db_size_kb']} KB")
            print(f"{'─' * 40}")

        elif args.command == "export":
            result = ltm.export(format=args.format, filepath=args.output)
            if args.output:
                print(result)
            else:
                print(result)

        elif args.command == "add":
            mem_id = ltm.add(role=args.role, content=args.content, tags=args.tags)
            print(f"✅ Added memory #{mem_id} (role={args.role})")

    finally:
        ltm.close()


if __name__ == "__main__":
    main()
