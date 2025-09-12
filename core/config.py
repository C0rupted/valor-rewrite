from dotenv import load_dotenv
import os, json


# Load environment variables from a .env file (if present)
load_dotenv()


class Config:
    # Discord bot token
    TOKEN = os.getenv("DISCORD_TOKEN")

    # Owner user ID as int, defaults to 0 if not set or invalid
    OWNER_ID = int(os.getenv("OWNER_ID", 0))

    # Boolean flag to indicate if the bot is in testing mode
    TESTING = os.getenv("TESTING", "false").lower() == "true"

    # Database connection parameters
    DB_HOST = os.getenv("DATABASE_HOST")
    DB_PORT = int(os.getenv("DATABASE_PORT", 3306))  # default MySQL port
    DB_USER = os.getenv("DATABASE_USER")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD")
    DB_NAME = os.getenv("DATABASE_NAME")

    # API key for Hypixel API
    HYPIXEL_API_KEY = os.getenv("HYPIXEL_API_KEY")

    # Guild IDs where ANO commands are enabled (stored as JSON array in env)
    ANO_COMMANDS_GUILD_IDS = json.loads(os.getenv("ANO_COMMANDS_GUILD_IDS"))

    # Role IDs or names for ANO members and military ranks
    ANO_MEMBER_ROLES = {int(role) for role in json.loads(os.getenv("ANO_MEMBER_ROLES"))}
    ANO_MILITARY_ROLES = {int(role) for role in json.loads(os.getenv("ANO_MILITARY_ROLES"))}

    # Lists of role IDs for high ranks, titans, chiefs in ANO
    ANO_HIGH_RANK_ROLES = {int(role) for role in json.loads(os.getenv("ANO_HIGH_RANK_ROLES"))}
    ANO_TITAN_ROLES = {int(role) for role in json.loads(os.getenv("ANO_TITAN_ROLES"))}
    ANO_CHIEF_ROLES = {int(role) for role in json.loads(os.getenv("ANO_CHIEF_ROLES"))}

    # Channel ID for Titan chat, parsed from JSON (usually a number or list)
    TITAN_CHAT_CHANNEL_ID = json.loads(os.getenv("TITAN_CHAT_CHANNEL_ID"))



# Create a global config instance to import elsewhere
config = Config()
