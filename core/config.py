from dotenv import load_dotenv
import os, json

load_dotenv()

class Config:
    TOKEN = os.getenv("DISCORD_TOKEN")
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
    TESTING = os.getenv("TESTING", "false").lower() == "true"

    DB_HOST = os.getenv("DATABASE_HOST")
    DB_PORT = int(os.getenv("DATABASE_PORT", 3306))
    DB_USER = os.getenv("DATABASE_USER")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD")
    DB_NAME = os.getenv("DATABASE_NAME")

    HYPIXEL_API_KEY = os.getenv("HYPIXEL_API_KEY")

    ANO_COMMANDS_GUILD_IDS = json.loads(os.getenv("ANO_COMMANDS_GUILD_IDS"))
    ANO_MEMBER_ROLE = os.getenv("ANO_MEMBER_ROLE")
    ANO_MILITARY_ROLE = os.getenv("ANO_MILITARY_ROLE")
    ANO_HIGH_RANK_ROLES = json.loads(os.getenv("ANO_HIGH_RANK_ROLES"))
    ANO_TITAN_ROLES = json.loads(os.getenv("ANO_TITAN_ROLES"))
    ANO_CHIEF_ROLES = json.loads(os.getenv("ANO_CHIEF_ROLES"))

    TITAN_CHAT_CHANNEL_ID = json.loads(os.getenv("TITAN_CHAT_CHANNEL_ID"))

config = Config()
