class Locale(dict):
    def __init__(self, language:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language

    def __repr__(self):
        #This makes the language string printable.
        return f"Locale('{self.language}', {super().__repr__()})"