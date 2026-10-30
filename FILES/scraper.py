"""
scraper.py — Local headless web scraper and researcher using Obscura browser.

Features:
- Executes local FILES/bin/obscura.exe with --stealth and zero telemetry.
- One-shot CLI subprocess execution (lazy start, terminates immediately).
- Extracts clean markdown directly without saving permanent files on disk.
- Refines and caps content to 5000-7000 words.
- Integrates seamlessly with LLaMA LLM via Responder.
"""

import os
import re
import urllib.parse
import subprocess
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

# Base path to obscura binary
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OBSCURA_BIN = os.path.join(BASE_DIR, "bin", "obscura.exe")

MAX_WORDS_CAP = 6000


def get_obscura_bin() -> str:
    """Returns absolute path to obscura binary if it exists."""
    if os.path.isfile(OBSCURA_BIN):
        return OBSCURA_BIN
    # Fallback to PATH
    return "obscura.exe"


@track_latency("scraper.refine_markdown")
def refine_markdown(content: str, max_words: int = MAX_WORDS_CAP) -> str:
    """
    Refines raw scraped markdown:
    - Strips consecutive empty lines and noise.
    - Limits word count to 5000-7000 words to respect LLaMA context budget.
    """
    if not content:
        return ""

    # Remove excessive blank lines
    cleaned = re.sub(r'\n{3,}', '\n\n', content).strip()

    # Cap to max words
    words = cleaned.split()
    if len(words) > max_words:
        cleaned = " ".join(words[:max_words]) + "\n\n[Content truncated for context limit]"

    return cleaned


@track_latency("scraper.scrape_url")
def scrape_url(url: str, timeout: int = 15) -> str:
    """
    Fetches and renders a URL using local obscura.exe in stealth mode.
    Returns clean markdown.
    """
    bin_path = get_obscura_bin()
    if not os.path.isfile(bin_path):
        logger.error(f"Obscura binary not found at: {bin_path}")
        return ""

    logger.info(f"Scraping URL via Obscura: {url}")
    cmd = [
        bin_path,
        "fetch",
        url,
        "--dump", "markdown",
        "--stealth",
        "-q"
    ]

    try:
        startupinfo = None
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=creationflags
        )

        if result.returncode == 0:
            logger.info(f"Successfully scraped {len(result.stdout)} characters from {url}")
            return result.stdout
        else:
            logger.warning(f"Obscura exited with code {result.returncode}: {result.stderr.strip()}")
            return ""
    except subprocess.TimeoutExpired:
        logger.error(f"Obscura timed out fetching: {url}")
        return ""
    except Exception as e:
        logger.error(f"Failed to execute Obscura: {e}", exc_info=True)
        return ""


@track_latency("scraper.search_links")
def search_links(query: str, max_results: int = 3) -> list:
    """
    Searches DuckDuckGo HTML using Obscura to extract top search result links.
    100% local without third-party search APIs.
    """
    bin_path = get_obscura_bin()
    encoded_query = urllib.parse.quote_plus(query)
    search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

    cmd = [
        bin_path,
        "fetch",
        search_url,
        "--dump", "links",
        "--stealth",
        "-q"
    ]

    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=creationflags
        )

        urls = []
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "uddg=" in line:
                    match = re.search(r'uddg=([^&\s]+)', line)
                    if match:
                        decoded_url = urllib.parse.unquote(match.group(1))
                        if decoded_url.startswith("http") and not any(skip in decoded_url for skip in ["duckduckgo.com"]):
                            if decoded_url not in urls:
                                urls.append(decoded_url)
                                if len(urls) >= max_results:
                                    break
        logger.info(f"Found {len(urls)} target links for query '{query}': {urls}")
        return urls
    except Exception as e:
        logger.error(f"Error searching links for query '{query}': {e}", exc_info=True)
        return []


@track_latency("scraper.search_and_scrape")
def search_and_scrape(query: str) -> str:
    """
    Given a search query or a direct URL:
    1. Resolves target URL.
    2. Scrapes rendered markdown via Obscura.
    3. Refines text (capped at 5000-7000 words).
    Returns refined text ready for LLM context.
    """
    # Check if query contains direct URL
    url_match = re.search(r'https?://[^\s]+', query)
    target_url = url_match.group(0) if url_match else None

    if not target_url:
        # Search DuckDuckGo for top URL
        links = search_links(query, max_results=1)
        if links:
            target_url = links[0]

    if not target_url:
        logger.warning(f"Could not find any target URL for query: {query}")
        return ""

    raw_markdown = scrape_url(target_url)
    if not raw_markdown:
        return ""

    refined = refine_markdown(raw_markdown, max_words=MAX_WORDS_CAP)
    return refined

