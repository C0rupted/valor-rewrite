from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    TOKEN = os.getenv("DISCORD_TOKEN")
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    DB_HOST = os.getenv("DATABASE_HOST")
    DB_PORT = int(os.getenv("DATABASE_PORT", 3306))
    DB_USER = os.getenv("DATABASE_USER")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD")
    DB_NAME = os.getenv("DATABASE_NAME")

settings = Config()
