import requests
from bs4 import BeautifulSoup
import urllib.parse
from duckduckgo_search import DDGS
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

@track_latency("web_search_extractor.extract_web_data")
def extract_web_data(query: str, max_results: int = 5, max_images: int = 5) -> dict:
    """
    Extracts data from web searches for a given query locally.
    It scrapes related text, relative links, and 1 to 5 images.
    """
    data = {
        "query": query,
        "details": [],
        "links": [],
        "images": []
    }
    
    # 1. Fetch comprehensive details from Wikipedia API manually
    try:
        wiki_search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&utf8=&format=json"
        res = requests.get(wiki_search_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            search_data = res.json()
            if search_data.get('query', {}).get('search'):
                title = search_data['query']['search'][0]['title']
                
                # Fetch extract and images
                detail_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts|pageimages&exintro&explaintext&titles={urllib.parse.quote(title)}&format=json&pithumbsize=500"
                detail_res = requests.get(detail_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                if detail_res.status_code == 200:
                    pages = detail_res.json().get('query', {}).get('pages', {})
                    for page_id, page_info in pages.items():
                        if 'extract' in page_info:
                            data['details'].append(page_info['extract'])
                        if 'thumbnail' in page_info:
                            data['images'].append(page_info['thumbnail']['source'])
                        
                        # Add link
                        page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"
                        data['links'].append({"title": f"{title} - Wikipedia", "url": page_url})
    except Exception as e:
        logger.warning(f"Wikipedia search failed: {e}")

    # 2. Scrape DuckDuckGo HTML directly as fallback/additional info
    try:
        ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        html_res = requests.get(ddg_url, headers=headers, timeout=10)
        
        if html_res.status_code == 200:
            soup = BeautifulSoup(html_res.text, 'html.parser')
            
            for a in soup.find_all('a', class_='result__url', limit=max_results):
                link = a.get('href', '')
                if link and not link.startswith('//duckduckgo'):
                    title_tag = a.find_previous('a', class_='result__snippet')
                    title = title_tag.text if title_tag else "Link"
                    
                    snippet = a.find_previous('a', class_='result__snippet')
                    if snippet and len(data['details']) < max_results:
                         data['details'].append(snippet.text)
                        
                    data['links'].append({"title": title, "url": link})
    except Exception as e:
        logger.warning(f"DuckDuckGo HTML search error: {e}")

    # 3. Use DuckDuckGo Search API (ddgs) as secondary for images
    try:
        ddgs = DDGS()
        if len(data["images"]) < max_images:
            image_results = list(ddgs.images(query, max_results=max_images))
            for img in image_results:
                if 'image' in img and img['image'] not in data["images"]:
                    data["images"].append(img.get("image", ""))
                    if len(data["images"]) >= max_images:
                        break
    except Exception as e:
         pass
            
    if not data["details"] and not data["links"] and not data["images"]:
        data["error"] = "Could not fetch any data for the given query."
        
    return data

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
