

class EDIT:
    def __init__(self, text:str, FROM_str:list, TO_str:list=None):
        self.original_text  : str  = str(text).lower()
        self.FROM_str       : list = list(FROM_str)
        self.TO_str         : list = list(TO_str)
    
    def replace_to_none(self):
        text = self.original_text
        for i in range( int(len(self.FROM_str)) ):
            text = text.replace( str(self.FROM_str[i]).lower() , "")

        return text
    
    def replace(self):
        text = self.original_text
        for i in range( int(len(self.FROM_str)) ):
            try:
                text = text.replace( str(self.FROM_str[i]).lower() , str(self.TO_str[i]))
            except: 
                text = text.replace( str(self.FROM_str[i]).lower() , str(self.TO_str[0]))
            

        return text
