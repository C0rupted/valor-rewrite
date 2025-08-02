import asyncio

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


async def get_names_from_uuids(uuids: list[str]) -> dict[str, str]:
    if not uuids:
        return {}

    # Look up existing cached names
    placeholders = ",".join(["%s"] * len(uuids))
    query = f"SELECT uuid, name FROM uuid_name WHERE uuid IN ({placeholders})"
    rows = await Database.fetch(query, tuple(uuids))

    names: dict[str, str] = {row["uuid"]: row["name"] for row in rows}
    missing = [uuid for uuid in uuids if uuid not in names]

    # Query Mojang API for any missing UUIDs
    if missing:
        fetched = await asyncio.gather(*(request(f"https://api.mojang.com/user/profile/{uuid.replace('-', '')}") for uuid in missing))

        inserts = []
        for uuid, res in zip(missing, fetched):
            if res and "name" in res:
                names[uuid] = res["name"]
                inserts.append((uuid, res["name"]))

        # Step 3: Cache new entries
        if inserts:
            for insert in inserts:
                await Database.fetch("INSERT INTO uuid_name (uuid, name) VALUES (%s, %s)", insert)

    return names
