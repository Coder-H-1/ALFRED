
class Memory:
    "Memory of previous commands given by user"

    def __init__(self):
        self.store = {
            "user_name": "sir",
            "last_command": None,
            "conversation_history": [],
            "session_history" : []
        }
        self._calls = 0

    def remember(self, key, value):
        "sets a key in self.store to value"

        self.store[key] = value


    def clean_history(self):
        "Cleans every session conversions"
            
        length = len(self.store["conversation_history"])
        for _ in range(length - (int(length/2))):
            self.store["conversation_history"].pop(0)
            
    def recall(self, key):
        return self.store.get(key, "")

    def add_to_history(self, prompt, response) -> None:
        self.store["conversation_history"].append((prompt, response))
        self.store["session_history"].append((prompt, response))

        if len(self.store["conversation_history"]) > 5:
            self.store["conversation_history"].pop(0)  # Keep recent 5

        if self._calls > 50:
            self.session_end()
        self._calls += 1

    def get_history(self) -> str:
        """
        Returns session chats in string 
        """
        return "\n".join(
            f"User: {q}\nButler: {a}" for q, a in self.store["conversation_history"]
        )
    
    def session_end(self) -> None:
        """
        writes entries to the file of chats of a session end.
        """
        History = "\n".join(
            f"User: {q} > Butler: {a}" for q, a in self.store["session_history"]
        )
        with open(f"FILES\\Mem\\mem.bin" , "w") as file:
            file.write(f"{History}")

    def get_previous_chats(self) -> list:
        """
        Return a list of previous chats \n
        \n
        Return Format :\n 
            User: {query} > Butler: {reply} 
            \n
        """
        return [i.strip() for i in open(f"FILES\\Mem\\mem.mem" , "r")]

    def Check_for_in_chats(self, text:str) -> str:
        """
        Search for previous replies in text\n
        if found    :-> return str\n
        else        :-> None   

        """
        Chats = self.get_previous_chats()
        for index, lines in enumerate(Chats):
            if text in lines:
                return str(Chats[index]).split(" > ")[1]
        
        return None



MEMORY = Memory()
