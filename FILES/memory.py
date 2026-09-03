"""
memory.py — Short-term RAM cache + Long-term SQLite persistence for ALFRED.
"""

from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

try:
    from FILES.long_term_memory import LongTermMemory
except ModuleNotFoundError:
    from long_term_memory import LongTermMemory


class Memory:
    """Memory of previous commands given by user — RAM cache + LTM persistence"""

    def __init__(self):
        self.store = {
            "user_name": "sir",
            "last_command": None,
            "conversation_history": [],
            "session_history": []
        }
        self._calls = 0

        # Long-term memory (SQLite) — starts a new session on init
        logger.info("Initializing Memory module and starting a new LTM session.")
        self._ltm = LongTermMemory()
        self._ltm.start_session()

    @track_latency("Memory.remember")
    def remember(self, key, value):
        """Sets a key in self.store to value"""
        logger.debug(f"Memory remember key: '{key}'")
        self.store[key] = value

    @track_latency("Memory.clean_history")
    def clean_history(self):
        """Clears every session conversions"""
        logger.info("Cleaning short-term conversation history cache.")
        length = len(self.store["conversation_history"])
        for _ in range(length - (int(length / 2))):
            self.store["conversation_history"].pop(0)

    @track_latency("Memory.recall")
    def recall(self, key):
        """Retrieves value for key in (self.store)"""
        val = self.store.get(key, "")
        logger.debug(f"Memory recall key '{key}'")
        return val

    @track_latency("Memory.add_to_history")
    def add_to_history(self, prompt, response) -> None:
        """Adds (user_input and reply) to history — persists to SQLite"""
        logger.info("Adding interaction exchange to history cache and SQLite LTM.")
        self.store["conversation_history"].append((prompt, response))
        self.store["session_history"].append((prompt, response))

        if len(self.store["conversation_history"]) > 5:
            self.store["conversation_history"].pop(0)  # Keep recent 5

        # Persist to long-term memory
        try:
            self._ltm.add_exchange(prompt, response)
        except Exception as e:
            logger.error(f"Failed to persist exchange to LTM SQLite: {e}", exc_info=True)

        if self._calls > 50:
            logger.info("Session exchanges count exceeded 50; triggering automatic session end.")
            self.session_end()
        self._calls += 1

    @track_latency("Memory.get_history")
    def get_history(self) -> str:
        """Returns session chats in string"""
        return "\n".join(
            f"User: {q}\nButler: {a}" for q, a in self.store["conversation_history"]
        )

    @track_latency("Memory.session_end")
    def session_end(self, generate_summary: bool = True) -> None:
        """
        Ends the current session. 
        Generates a 1-line summary from session history and persists to LTM.
        """
        logger.info("Ending Memory session.")
        summary = ""
        if generate_summary and self.store["session_history"]:
            # Build a simple summary from first and last topics
            topics = []
            for q, _ in self.store["session_history"]:
                short = q.strip()[:30]
                if short and short not in topics:
                    topics.append(short)
            
            if len(topics) <= 3:
                summary = "Topics: " + ", ".join(topics)
            else:
                summary = f"Topics: {topics[0]}, {topics[1]}, ... {topics[-1]} ({len(topics)} exchanges)"

        try:
            self._ltm.end_session(summary=summary)
            logger.info("LTM session ended successfully.")
        except Exception as e:
            logger.error(f"Failed to end LTM session: {e}", exc_info=True)
            
        self.store["session_history"] = []

    @track_latency("Memory.get_previous_chats")
    def get_previous_chats(self, limit: int = 20) -> list:
        """
        Return a list of previous chats from long-term memory.
        """
        logger.debug(f"Fetching previous chats from LTM (limit: {limit})")
        try:
            results = self._ltm.search_by_date(
                start_date="2020-01-01",
                end_date="2099-12-31"
            )
            formatted = []
            for r in results[-limit:]:
                prefix = "User" if r['role'] == 'user' else "Butler"
                formatted.append(f"{prefix}: {r['content']}")
            return formatted
        except Exception as e:
            logger.error(f"Failed to fetch previous chats: {e}", exc_info=True)
            return []

    @track_latency("Memory.Check_for_in_chats")
    def Check_for_in_chats(self, text: str) -> str:
        """
        Search for previous replies containing text.
        if found  :-> return str
        else      :-> None
        """
        logger.debug(f"Checking in-chats matching text: '{text}'")
        try:
            results = self._ltm.search(text)
            for r in results:
                if r['role'] == 'alfred':
                    return r['content']
        except Exception as e:
            logger.error(f"Failed to search LTM in-chats: {e}", exc_info=True)
        return None

    @track_latency("Memory.get_last_assistant_response")
    def get_last_assistant_response(self) -> str:
        """
        Retrieves the most recent ALFRED response from Long Term Memory (SQLite),
        falling back to short term cache.
        """
        try:
            cur = self._ltm._conn.cursor()
            row = cur.execute(
                "SELECT content FROM memories WHERE role = 'alfred' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row and row["content"]:
                return row["content"]
        except Exception as e:
            logger.error(f"Failed to fetch last assistant response from LTM SQLite: {e}", exc_info=True)

        if self.store["conversation_history"]:
            for _, reply in reversed(self.store["conversation_history"]):
                if reply:
                    return reply
        return ""



MEMORY = Memory()  # Creates Global Memory Object