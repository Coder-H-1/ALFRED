import requests

def get_Data_state() -> bool:
    try:
        requests.get(f"https://www.google.com")
        return True
    except:
        return False
