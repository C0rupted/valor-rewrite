from database.connection import Database
from util.requests import request

def format_uuid(raw: str) -> str:
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"

async def get_uuid_from_name(player: str) -> str | None:
    if "-" in player:
        return None

    result = await Database.fetch("SELECT uuid FROM uuid_name WHERE name=%s LIMIT 1", (player))
    if result:
        return result[0]["uuid"]

    res = await request(f"https://api.mojang.com/users/profiles/minecraft/{player}")
    if not res:
        return None

    formatted = format_uuid(res["id"])
    await Database.fetch("INSERT INTO uuid_name (uuid, name) VALUES (%s, %s)", (formatted, player))
    return formatted

async def get_name_from_uuid(uuid: str):
    res = await Database.fetch("SELECT * FROM uuid_name WHERE uuid=%s LIMIT 1", (uuid))

    if res:
        return res[0]["name"]

    res = await request(f"https://api.mojang.com/user/profile/{uuid.replace('-', '')}")

    if not res:
        return None

    await Database.fetch("INSERT INTO uuid_name VALUES (%s, %s)", (uuid, res["name"]))
    
    return res["name"]