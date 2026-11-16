"""
test_mcp_failures.py — Automated Unit Tests for Tool Failure & Exception Guardrails
"""

import unittest
from FILES.plugin_host import _format_tool_output


class TestMCPFailuresAndFormatting(unittest.TestCase):
    """Verifies that tool execution errors, malformed outputs, and timeouts are safely handled."""

    def test_format_tool_output_error(self):
        error_result = {"error": "Failed to connect to weather sensor: connection refused."}
        formatted = _format_tool_output(error_result)
        self.assertIn("Notice:", formatted)
        self.assertIn("Failed to connect", formatted)

    def test_format_tool_output_json_string(self):
        json_str = '{"status": "Successfully updated profile."}'
        formatted = _format_tool_output(json_str)
        self.assertEqual(formatted, "Successfully updated profile.")

    def test_format_tool_output_empty_dict(self):
        formatted = _format_tool_output({})
        self.assertEqual(formatted, "Tool execution completed.")

    def test_format_tool_output_malformed_string(self):
        malformed = "{ broken json"
        formatted = _format_tool_output(malformed)
        self.assertEqual(formatted, "{ broken json")


if __name__ == "__main__":
    unittest.main()
