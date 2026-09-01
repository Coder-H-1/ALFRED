from FILES.long_term_memory import LongTermMemory
from FILES.utils import clear_Memory
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)
LTM = LongTermMemory()

@track_latency("commands.process_command.repeat_answer")
def handle_repeat_answer(command: str) -> str:
    try:
        logger.info("Recalling previous assistant response")
        output = LTM.print_memories(limit=2)
        lines = output.split('\n')
        for line in lines:
            if "ALFRED:" in line and "repeat" not in line.lower():
                response = line.split("ALFRED:")[1].strip()
                if response:
                    return response
        
        conn = LTM.get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT content FROM memories 
            WHERE role = 'assistant' 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        row = c.fetchone()
        conn.close()
        if row:
            return row[0]
        
        return "I have no recent memory to repeat, sir."
    except Exception as e:
        logger.error(f"Error repeating answer: {e}", exc_info=True)
        return "I could not retrieve my previous answer, sir."

@track_latency("commands.process_command.clear_memory")
def handle_clear_memory(command: str) -> str:
    logger.info("Clearing memory history")
    clear_Memory()
    return "Cleared Memory at your command"

@track_latency("commands.process_command.search_memory")
def handle_search_memory(command: str) -> str:
    parts = command.split("memory", 1) if "memory" in command else command.split("recall", 1)
    if len(parts) > 1 and parts[1].strip():
        query = parts[1].strip()
        logger.info(f"Searching memory for: '{query}'")
        results = LTM.search(query)
        if results:
            snippets = []
            for r in results[:5]:
                prefix = "You said" if r['role'] == 'user' else "I replied"
                content = r['content'][:80]
                snippets.append(f"{prefix}: {content}")
            return "Here is what I found in my memory, sir:\n" + "\n".join(snippets)
        else:
            return "I'm afraid I found nothing matching that in my memory, sir."
    else:
        return "What would you like me to search for in my memory, sir?"

@track_latency("commands.process_command.show_memory")
def handle_show_memory(command: str) -> str:
    logger.info("Printing memory statistics/details to terminal")
    output = LTM.print_memories(limit=10)
    print(output)
    return "I've displayed my recent memories on the terminal, sir."

@track_latency("commands.process_command.memory_stats")
def handle_memory_stats(command: str) -> str:
    logger.info("Getting memory database stats")
    s = LTM.stats()
    return (f"I have {s['total_memories']} memories across {s['total_sessions']} sessions. "
            f"Database size is {s['db_size_kb']} kilobytes.")

@track_latency("commands.process_command.forget_conversation")
def handle_forget_conversation(command: str) -> str:
    sid = LTM.get_current_session_id()
    if sid:
        logger.info(f"Deleting conversation session ID: {sid}")
        count = LTM.delete_session(sid)
        return f"Done. I've forgotten {count} memories from this session."
    else:
        return "There is no active session to forget, sir."
