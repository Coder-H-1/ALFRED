import requests
import os
from FILES.logger import get_logger

logger = get_logger(__name__)

def extract_web_data(query: str, max_results: int = 5, max_images: int = 5) -> dict:
    """
    Extracts data from web searches for a given query by hitting the backend API.
    
    Args:
        query: The search term (e.g., "Iron man")
        max_results: Max number of links/texts to fetch
        max_images: Max number of images to fetch
        
    Returns:
        dict: A dictionary containing 'query', 'details', 'links', and 'images'
    """
    base_backend_url = os.getenv("RENDER_BACKEND_URL")
    # Clean ending slash and append /api/search/
    backend_url = base_backend_url.rstrip("/") + "/api/search/"
    
    logger.info(f"Extracting web data for: '{query}' via backend: {backend_url}")
    
    try:
        res = requests.get(backend_url, params={"q": query, "max_results": max_results, "max_images": max_images}, timeout=30)
        if res.status_code == 200:
            logger.info("Successfully fetched search results from backend.")
            return res.json()
        else:
            logger.warning(f"Backend returned status {res.status_code}")
            return {
                "query": query,
                "details": [],
                "links": [],
                "images": [],
                "error": f"Backend returned status {res.status_code}"
            }
    except Exception as e:
        logger.error(f"Failed to fetch search results from backend: {e}", exc_info=True)
        return {
            "query": query,
            "details": [],
            "links": [],
            "images": [],
            "error": str(e)
        }

if __name__ == "__main__":
    import sys
    test_query = "Iron man" if len(sys.argv) == 1 else " ".join(sys.argv[1:])
    print(f"Fetching data for: {test_query}...\n")
    
    result = extract_web_data(test_query)
    
    if result.get("error"):
        print(f"Error: {result['error']}")
    else:
        print("--- DETAILS ---")
        for i, detail in enumerate(result['details'], 1):
            print(f"{i}. {detail}")
            
        print("\n--- LINKS ---")
        for i, link in enumerate(result['links'], 1):
            print(f"{i}. {link['title'][:30]} - {link['url']}")
            
        print("\n--- IMAGES ---")
        for i, img in enumerate(result['images'], 1):
            print(f"{i}. {img}")
