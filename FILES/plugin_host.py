"""
`plugin_host.py` — Octopus MCP Intermediary Bridge Adapter for ALFRED

Connects ALFRED's synchronous command loop to FmWk's Octopus MCP Bridge.
Eliminates insecure raw socket code injection and integrates Strategy B tool execution.
"""

from typing import Optional, Any, Dict
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency
from FmWk.bridge import get_bridge

logger = get_logger(__name__)


def _format_tool_output(result: Any) -> str:
    """Formats raw tool results into natural spoken text for ALFRED."""
    if isinstance(result, str):
        trimmed = result.strip()
        if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
            try:
                import json
                parsed = json.loads(trimmed)
                return _format_tool_output(parsed)
            except Exception:
                pass
        return result

    if isinstance(result, dict):
        prefix = "[KEEP_UI] " if result.get("keep_ui") else ""
        if "status" in result:
            return f"{prefix}{result['status']}"
        if "answer" in result:
            return f"{prefix}{result['answer']}"
        if "results" in result:
            res_list = result["results"]
            if isinstance(res_list, list) and res_list:
                return f"{prefix}{str(res_list[0])}"
            return f"{prefix}{str(res_list)}"
        if "content" in result:
            items = result["content"]
            if isinstance(items, list) and items and isinstance(items[0], dict) and "text" in items[0]:
                text_content = items[0]["text"]
                trimmed = text_content.strip()
                if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
                    try:
                        import json
                        parsed = json.loads(trimmed)
                        return f"{prefix}{_format_tool_output(parsed)}"
                    except Exception:
                        pass
                return f"{prefix}{text_content}"
            return f"{prefix}{str(items)}"
        if "messages" in result:
            msgs = result["messages"]
            if isinstance(msgs, list):
                if not msgs:
                    return f"{prefix}Your inbox is clear with zero unread messages, sir."
                count = len(msgs)
                first = msgs[0]
                first_text = first.get("subject") or first.get("snippet") or "no subject"
                return f"{prefix}Sir, you have {count} recent message(s). Most recent: '{first_text}'."
        if "message" in result:
            return f"{prefix}{result['message']}"
        if "error" in result:
            return f"Notice: {result['error']}"
        # Fallback dictionary display
        parts = [f"{k}: {v}" for k, v in result.items() if not k.startswith("_")]
        return f"{prefix}{', '.join(parts)}" if parts else "Tool execution completed."

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


def test_mcp_tools(query: Optional[str] = None, verbose: bool = True) -> Dict[str, Any]:
    """
    Test function for MCP tools.
    Measures startup time, tools found, query received, and tools output.
    """
    import time
    from FmWk.core.decorators import get_local_tools

    t0 = time.perf_counter()
    bridge = get_bridge()
    tools = bridge.get_all_tool_schemas()
    startup_time_ms = (time.perf_counter() - t0) * 1000

    local_tools = get_local_tools()
    test_query = query or "check system status"

    q_start = time.perf_counter()
    routing_res = bridge.route_and_execute(test_query)
    exec_time_ms = (time.perf_counter() - q_start) * 1000

    handled = routing_res.get("handled", False)
    raw_result = routing_res.get("result")
    formatted = _format_tool_output(raw_result) if handled else None

    report = {
        "startup_time_ms": startup_time_ms,
        "tools_found": {
            "total_count": len(tools),
            "local_count": len(local_tools),
            "tool_names": [t["name"] for t in tools],
        },
        "query_received": test_query,
        "tools_output": {
            "handled": handled,
            "strategy": routing_res.get("strategy", routing_res.get("reason", "unknown")),
            "tool_name": routing_res.get("tool"),
            "arguments": routing_res.get("arguments", {}),
            "raw_result": raw_result,
            "formatted_speech": formatted,
            "execution_time_ms": exec_time_ms,
        },
        "program_outputs": {
            "status": "success" if handled else "cascaded_to_llm",
            "execution_time_ms": exec_time_ms,
        }
    }

    if verbose:
        print(f"[STARTUP TIME]  : {startup_time_ms:.2f} ms")
        print(f"[TOOLS FOUND]   : {len(tools)} tools registered ({len(local_tools)} local)")
        print(f"[QUERY RECEIVED] : \"{test_query}\"")
        print(f"[TOOLS OUTPUT]   : Handled={handled}, Tool={routing_res.get('tool')}, Speech='{formatted}'")
        print(f"[PROGRAM OUTPUTS]: Status={report['program_outputs']['status']} in {exec_time_ms:.2f} ms")

    return report

