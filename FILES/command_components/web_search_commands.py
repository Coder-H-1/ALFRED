"""
web_search_commands.py — Handles web scraping and online queries using local Obscura browser.
"""

import re
from FILES.scraper import search_and_scrape
from FILES.utils import Responder
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

@track_latency("commands.process_command.web_search")
def handle_web_search(command: str) -> str:
    """
    Extracts search query, fetches web data via Obscura, and synthesizes response with local LLM.
    Cleans all temporary data immediately.
    """
    # Clean trigger phrases
    clean_query = command
    for prefix in [
        "search the web for",
        "search online for",
        "search the internet for",
        "search for",
        "look up online",
        "look up on web",
        "look up on the web",
        "browse the web for",
        "scrape website",
        "scrape url",
        "scrape"
    ]:
        if prefix in clean_query:
            clean_query = clean_query.replace(prefix, "").strip()
            break

    if not clean_query:
        return "What would you like me to search for on the web, sir?"

    logger.info(f"Executing web research via Obscura for query: '{clean_query}'")
    scraped_context = search_and_scrape(clean_query)

    if not scraped_context:
        logger.warning("No web data could be scraped.")
        return f"I was unable to retrieve live web data for {clean_query}, sir."

    prompt = (
        f"You are ALFRED, a personal AI assistant. "
        f"The user asked: '{clean_query}'.\n\n"
        f"Here is real-time scraped information from the web:\n"
        f"\"\"\"\n{scraped_context}\n\"\"\"\n\n"
        f"Answer the user's question concisely based on the scraped web information."
    )

    return Responder(prompt)

