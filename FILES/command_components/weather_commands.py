import os
import requests
from FILES.utils import Responder
from FILES.logger import get_logger
from FILES.LATENCY_RECORDER import track_latency

logger = get_logger(__name__)

@track_latency("commands.process_command.weather")
def handle_weather(command: str) -> str:
    try:
        api_key = os.getenv("OpenWeatherKey")
        if not api_key:
            return "No OpenWeatherKey found in environment variables, sir."
        
        logger.info("Fetching weather...")
        ip_info = requests.get("http://ip-api.com/json/", timeout=5).json()
        lat = ip_info.get("lat")
        lon = ip_info.get("lon")
        city = ip_info.get("city", "Unknown location")
        
        if lat and lon:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            res = requests.get(url, timeout=5).json()
            weather_data = {"weather": res, "city": city}
            prompt = f"The user wants to check the weather. The JSON data is {weather_data}. Answer the user based on this data."
            return Responder(prompt)
        else:
            return "Could not determine location coordinates, sir."
    except Exception as e:
        logger.error(f"Failed to check weather: {e}", exc_info=True)
        return f"Failed to check weather: {str(e)}"
