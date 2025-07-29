import os

class Work:
    def __init__(self, filepath:str):
        self.content = []
        self.path = str(filepath)

    def readFile(self) -> list:
        if os.path.exists(f"{self.path}"):
            with open(f"{self.path}" , "r" ) as File:
                Content = File.readlines()
        self.content = list(Content)

    def Check(content:list) -> True:
        for lines in content:
            