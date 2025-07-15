import requests
from database.connection import Database

def format_uuid(raw: str) -> str:
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"

async def get_uuid(player: str) -> str | None:
    if "-" in player:
        return None

    result = await Database.fetch("SELECT uuid FROM uuid_name WHERE name=%s LIMIT 1", (player,))
    if result:
        return result[0]["uuid"]

    res = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{player}")
    if res.status_code != 200:
        return None

    uuid = res.json()["id"]
    formatted = format_uuid(uuid)
    await Database.execute("INSERT INTO uuid_name (uuid, name) VALUES (%s, %s)", (formatted, player))
    return formatted