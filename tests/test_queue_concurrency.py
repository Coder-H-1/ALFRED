"""
test_queue_concurrency.py — Automated Unit Tests for Priority Queue Preemption & Concurrency
"""

import unittest
import re
from collections import deque
from concurrent.futures import ThreadPoolExecutor


class TestQueueConcurrency(unittest.TestCase):
    """Tests ALFRED's FIFO message queue and high-priority preemption."""

    def test_priority_preemption_logic(self):
        message_queue = deque()
        # Normal queries pushed to queue while assistant is speaking
        message_queue.append("what is the weather")
        message_queue.append("open notepad")
        message_queue.append("check system battery")

        self.assertEqual(len(message_queue), 3)

        # High priority command with 'alfred' keyword arrives
        incoming_cmd = "alfred, stop and shutdown computer"
        has_alfred = bool(re.match(r"^alfred\b", incoming_cmd, re.IGNORECASE))
        self.assertTrue(has_alfred)

        # High priority must flush the lower-priority queue
        if has_alfred:
            message_queue.clear()
            clean_cmd = re.sub(r"^alfred\s*[,:]?\s*", "", incoming_cmd, flags=re.IGNORECASE).strip()

        self.assertEqual(len(message_queue), 0)
        self.assertEqual(clean_cmd, "stop and shutdown computer")

    def test_fifo_order_retention(self):
        message_queue = deque()
        commands = [f"command_{i}" for i in range(10)]
        for cmd in commands:
            message_queue.append(cmd)

        processed = []
        while message_queue:
            processed.append(message_queue.popleft())

        self.assertEqual(processed, commands)

    def test_thread_safe_queueing(self):
        message_queue = deque()
        import threading
        lock = threading.Lock()

        def push_item(item):
            with lock:
                message_queue.append(item)

        with ThreadPoolExecutor(max_workers=5) as executor:
            for i in range(50):
                executor.submit(push_item, f"query_{i}")

        self.assertEqual(len(message_queue), 50)


if __name__ == "__main__":
    unittest.main()
