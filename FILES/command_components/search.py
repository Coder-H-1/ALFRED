import os
import requests
import base64
import wikipedia
from FILES.gui_controller import show_data
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

@track_latency("commands.process_command.search")
def handle_search_query(command: str) -> str:
    """Handle Wikipedia / Online Web Search queries."""
    query = command.replace("who is ", "").replace("what is ", "").replace("tell me about ", "").strip()
    if not query:
        return None

    logger.info(f"Processing search/wikipedia query for: '{query}'")
    
    # 1. Try online search
    try:
        from FILES.web_search_extractor import extract_web_data
        search_res = extract_web_data(query)
        if search_res and not search_res.get("error") and search_res.get("details"):
            details = search_res.get("details", [])
            combined = " ".join([d.strip() for d in details if d.strip()][:2])
            if combined:
                logger.info("Online search via backend succeeded.")
                images = search_res.get("images", [])
                if images:
                    show_data(images[:3])
                return combined + " [KEEP_UI]"
    except Exception as e:
        logger.warning(f"Online backend search failed: {e}")

    # 2. Fallback to local Wikipedia library search
    try:
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Data", "temp_images")
        os.makedirs(temp_dir, exist_ok=True)
        
        for f in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, f))
            except Exception as e:
                logger.debug(f"Failed to remove temp image {f}: {e}")
        
        summary = wikipedia.summary(query, sentences=2)
        page = wikipedia.page(query, auto_suggest=False)
        
        images_b64 = []
        for img_url in page.images:
            if img_url.lower().endswith(('.jpg', '.jpeg', '.png')) and "svg" not in img_url.lower():
                try:
                    res = requests.get(img_url, timeout=5)
                    if res.status_code == 200:
                        filename = os.path.basename(img_url).split("?")[0]
                        filepath = os.path.join(temp_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(res.content)
                        
                        ext = "jpeg" if filename.lower().endswith(".jpg") else "png"
                        b64_data = base64.b64encode(res.content).decode('utf-8')
                        images_b64.append(f"data:image/{ext};base64,{b64_data}")
                        
                        if len(images_b64) >= 3:
                            break
                except Exception as e:
                    logger.debug(f"Failed to download image {img_url}: {e}")
        
        if images_b64:
            show_data(images_b64)
            
        logger.info("Wikipedia library query succeeded.")
        return summary + " [KEEP_UI]"
    except Exception as e:
        logger.warning(f"Wikipedia library search failed: {e}. Falling back to local LLM.")
        return None
