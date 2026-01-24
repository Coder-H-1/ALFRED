import os 

FILE = f"FILES/model/data"
DATA = ""

for lines in open(f"{FILE}/intents.jsonl", "r"):
    DATA += f"{lines}"
DATA += "\n"

def formater(query:str, answer:str) -> str:
    if "\"" in query:
        string = "{\"query\" : " + query + " , \"answer\" : \"??\"}\n".replace("??" , answer) 
    else:
        string = "{\"query\" : \"" + query +"\" , \"answer\" : \"??\"}\n".replace("??" , answer) 

    return string

for index, lines in enumerate(open(f"{FILE}/yesno.csv" , "r")):
    try: query, answer  = lines.replace("\n" , "").split(",")

    except: pass
    DATA += formater(query, (answer if answer!="None" else "Null"))

with open(f"testing.jsonl" , "w") as file:
    file.write(DATA)
print("done!") 

