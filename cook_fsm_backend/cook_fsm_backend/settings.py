import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.some_setting = os.getenv("SOME_SETTING", "default_value")

settings = Settings()
