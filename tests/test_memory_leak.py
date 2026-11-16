"""
test_memory_leak.py — Extended Session Multi-Turn Memory Simulation
"""

import unittest
import os
import tempfile
from FILES.long_term_memory import LongTermMemory


class TestMemoryExtendedSession(unittest.TestCase):
    """Tests SQLite connection stability and memory operations over extended turns."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_memory.db")
        self.ltm = LongTermMemory(db_path=self.db_path)

    def tearDown(self):
        self.ltm.close()
        self.temp_dir.cleanup()

    def test_multi_turn_session_stability(self):
        sid = self.ltm.start_session()
        # Simulate 100 turns of user-assistant interaction
        for i in range(100):
            self.ltm.add(role="user", content=f"Query {i}: What is quantum entanglement?", tags="physics")
            self.ltm.add(role="alfred", content=f"Response {i}: Entanglement is a physical phenomenon.", tags="physics")

        stats = self.ltm.stats()
        self.assertEqual(stats["total_memories"], 200)

        # Verify search works over large record set
        results = self.ltm.search("entanglement")
        self.assertTrue(len(results) > 0)

        # Verify deletion / clean up
        deleted = self.ltm.delete_session(sid)
        self.assertEqual(deleted, 200)
        self.assertEqual(self.ltm.stats()["total_memories"], 0)


if __name__ == "__main__":
    unittest.main()
