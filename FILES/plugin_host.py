"""
`plugin_host.py` — Octopus MCP Intermediary Bridge Adapter for ALFRED

Connects ALFRED's synchronous command loop to FmWk's Octopus MCP Bridge.
Eliminates insecure raw socket code injection and integrates Strategy B tool execution.
"""

from typing import Optional, Any
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency
from FmWk.bridge import get_bridge

logger = get_logger(__name__)


def _format_tool_output(result: Any) -> str:
    """Formats raw tool results into natural spoken text for ALFRED."""
    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        if "status" in result:
            return str(result["status"])
        if "answer" in result:
            return str(result["answer"])
        if "results" in result:
            res_list = result["results"]
            if isinstance(res_list, list) and res_list:
                return str(res_list[0])
            return str(res_list)
        if "message" in result:
            return str(result["message"])
        if "error" in result:
            return f"Notice: {result['error']}"
        # Fallback dictionary display
        parts = [f"{k}: {v}" for k, v in result.items() if not k.startswith("_")]
        return ", ".join(parts) if parts else "Tool execution completed."

    return str(result)


@track_latency("plugin_host.start_plugin_listener")
def start_plugin_listener():
    """
    Initializes the Octopus MCP Intermediary Bridge daemon on ALFRED launch.
    Discovers all local native tools and configured stdio MCP servers.
    """
    logger.info("Initializing Octopus MCP Bridge for ALFRED...")
    try:
        bridge = get_bridge()
        tools = bridge.get_all_tool_schemas()
        logger.info(f"Octopus MCP Bridge online. {len(tools)} tool(s) registered.")
    except Exception as e:
        logger.error(f"Failed to initialize Octopus MCP Bridge: {e}", exc_info=True)


@track_latency("plugin_host.match_dynamic_command")
def match_dynamic_command(command: str) -> Optional[str]:
    """
    Routes command through Octopus MCP using Strategy B:
    1. Fast-path regex / keyword router (sub-1ms).
    2. Optional local Qwen 4-bit tool classifier.
    3. If tool succeeds -> returns formatted result string.
    4. If no tool matches or tool fails -> returns None (cascades to ALFRED LLM).
    """
    if not command:
        return None

    try:
        bridge = get_bridge()
        res = bridge.route_and_execute(command)

        if res.get("handled"):
            raw_result = res.get("result")
            formatted = _format_tool_output(raw_result)
            tool_name = res.get("tool", "unknown_tool")
            logger.info(f"MCP Tool '{tool_name}' matched and executed successfully.")
            return formatted

    except Exception as e:
        logger.error(f"Error evaluating Octopus MCP dynamic command: {e}", exc_info=True)

    return None
