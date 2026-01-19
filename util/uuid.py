import asyncio, re

from database import Database
from util.requests import request
from pymysql.err import IntegrityError



def format_uuid(raw: str) -> str:
    """
    Format a raw 32-character UUID string by inserting dashes to match
    the standard UUID representation (8-4-4-4-12 characters).

    Args:
        raw (str): Raw UUID string without dashes.

    Returns:
        str: Formatted UUID string with dashes.
    """
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"



async def get_uuid_from_name(player: str) -> str | None:
    """
    Fetch the UUID for a given Minecraft player name.

    The function first attempts to find the UUID cached in the database.
    If not found, it queries Mojang's official API, caches the result, and returns it.

    Args:
        player (str): Minecraft player name.

    Returns:
        str | None: The player's UUID in formatted form if found, else None.
    """
    # If input contains a dash, assume it's not a username (could be UUID)
    if "-" in player:
        return None

    # Query cached UUID from database
    result = await Database.fetch("SELECT uuid FROM uuid_name WHERE name=%s LIMIT 1", (player,))
    if result:
        return result[0]["uuid"]

    # Query Mojang API for UUID
    res = await request(f"https://api.mojang.com/users/profiles/minecraft/{player}")
    if not res:
        return None

    # Format raw UUID string from Mojang API response
    formatted = format_uuid(res["id"])

    # Cache in database for future use
    try:
        await Database.fetch("INSERT INTO uuid_name (uuid, name) VALUES (%s, %s)", (formatted, player))
    except IntegrityError as e:
        # UUID already exists (user changed name), update the existing record
        if e.args[0] == 1062:  # Duplicate entry error
            await Database.fetch("UPDATE uuid_name SET name=%s WHERE uuid=%s", (player, formatted))
        else:
            raise
    return formatted



async def get_name_from_uuid(uuid: str) -> str | None:
    """
    Fetch the Minecraft player name for a given UUID.

    The function first attempts to find the name cached in the database.
    If not found, it queries Mojang's official API, caches the result, and returns it.

    Args:
        uuid (str): UUID string (with dashes).

    Returns:
        str | None: The player's name if found, else None.
    """
    # Query cached name from database
    res = await Database.fetch("SELECT * FROM uuid_name WHERE uuid=%s LIMIT 1", (uuid,))
    if res:
        return res[0]["name"]

    # Remove dashes for Mojang API call
    res = await request(f"https://api.mojang.com/user/profile/{uuid.replace('-', '')}")
    if not res:
        return None

    # Cache name in database for future use
    await Database.fetch("INSERT INTO uuid_name VALUES (%s, %s)", (uuid, res["name"]))
    return res["name"]



async def get_names_from_uuids(uuids: list[str]) -> dict[str, str]:
    """
    Given a list of UUIDs, fetch the corresponding player names.

    The function queries cached names from the database, then fetches any missing names from Mojang API
    in parallel, caching those results as well.

    Args:
        uuids (list[str]): List of UUID strings (with dashes).

    Returns:
        dict[str, str]: Mapping from UUID to player name for all provided UUIDs.
    """
    if not uuids:
        return {}

    # Prepare SQL placeholders for variable number of UUIDs
    placeholders = ",".join(["%s"] * len(uuids))
    query = f"SELECT uuid, name FROM uuid_name WHERE uuid IN ({placeholders})"

    # Fetch cached UUID-name mappings from database
    rows = await Database.fetch(query, tuple(uuids))
    names: dict[str, str] = {row["uuid"]: row["name"] for row in rows}

    # Find UUIDs missing from cache
    missing = [uuid for uuid in uuids if uuid not in names]

    # Fetch missing names concurrently from Mojang API
    if missing:
        fetched = await asyncio.gather(
            *(request(f"https://api.mojang.com/user/profile/{uuid.replace('-', '')}") for uuid in missing)
        )

        inserts = []
        # Process API responses and cache new mappings
        for uuid, res in zip(missing, fetched):
            if res and "name" in res:
                names[uuid] = res["name"]
                inserts.append((uuid, res["name"]))

        # Insert new UUID-name pairs into database
        if inserts:
            for insert in inserts:
                await Database.fetch("INSERT INTO uuid_name (uuid, name) VALUES (%s, %s)", insert)

    return names



def detect_uuid_or_name(value: str) -> str:
    """
    Detect whether a given string is a Minecraft UUID or username.

    The function uses regex to determine if the input matches the UUID format (with or without dashes)
    or the Minecraft username constraints (3-16 characters, alphanumeric + underscore).

    Args:
        value (str): Input string to check.

    Returns:
        str: One of "uuid", "name", or "invalid" depending on the detected type.
    """
    # Regex for UUID (32 hex chars optionally separated by dashes)
    uuid_regex = re.compile(
        r"^[0-9a-fA-F]{32}$|^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )

    # Regex for Minecraft username: 3-16 chars, alphanumeric and underscores allowed
    username_regex = re.compile(r"^[a-zA-Z0-9_]{3,16}$")

    if uuid_regex.match(value):
        return "uuid"
    elif username_regex.match(value):
        return "name"
    else:
        return "invalid"


