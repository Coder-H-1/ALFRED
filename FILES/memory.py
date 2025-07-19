class Memory:
    def __init__(self):
        self.store = {
            "user_name": "sir",
            "last_command": None,
            "conversation_history": []
        }

    def remember(self, key, value):
        self.store[key] = value

    def clean_history(self):
        self.store["conversation_history"] = []

    def recall(self, key):
        return self.store.get(key, "")

    def add_to_history(self, prompt, response):
        self.store["conversation_history"].append((prompt, response))
        if len(self.store["conversation_history"]) > 10:
            self.store["conversation_history"].pop(0)  # Keep recent 10

    def get_history(self):
        return "\n".join(
            f"User: {q}\nButler: {a}" for q, a in self.store["conversation_history"]
        )
    

def Memory_Alfred() -> str:
    return ""
