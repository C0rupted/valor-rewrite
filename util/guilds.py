import asyncio

from database import Database
from typing import List, Tuple, MutableSet
from util.requests import request
import logging


async def guild_name_from_tag(tag: str) -> str:
    if "--" in tag or ";" in tag: return None
    
    guilds = await Database.fetch(f"SELECT * FROM guild_tag_name WHERE LOWER(tag)='{tag.lower()}' ORDER BY priority DESC")
    
    if not len(guilds):
        return None
        
    if len(guilds) >= 2 and guilds[0]["priority"] == guilds[1]["priority"]:
        revisions = []

        for g, tag, _ in guilds:
            res = request("https://api.wynncraft.com/v3/guild/"+g)
            n_members = res["members"]["total"]
            revisions.append(f"('{g}','{tag}',{n_members})")

        await Database.fetch(f"REPLACE INTO guild_tag_name VALUES " + ','.join(revisions))
        revisions.sort(key=lambda x: x[2], reverse=True)
        
        return revisions[0]["guild"]
    
    return guilds[0]["guild"]



async def guild_tag_from_name(name: str) -> str:
    if "-" in name or ";" in name: return None
    
    guilds = await Database.fetch("SELECT * FROM guild_tag_name WHERE LOWER(guild)=%s ORDER BY priority DESC", (name.lower()))
    
    if not len(guilds):
        return None
    
    if len(guilds) >= 2 and guilds[0]["priority"] == guilds[1]["priority"]:
        revisions = []

        for g, tag, _ in guilds:
            res = request("https://api.wynncraft.com/v3/guild/"+g)
            n_members = res["members"]["total"]
            revisions.append(f"('{g}','{tag}',{n_members})")

        await Database.fetch(f"REPLACE INTO guild_tag_name VALUES " + ','.join(revisions))
        revisions.sort(key=lambda x: x[2], reverse=True)
        
        return revisions[0]["tag"]
    
    return guilds[0]["tag"]



async def guild_names_from_tags(tags: List[str]) -> Tuple[list[str], list[str]]:
    name_map: dict[str, str] = {}
    unidentified: list[str] = []

    # Clean input (skip obviously invalid tags)
    valid_tags = [t for t in tags if "--" not in t and ";" not in t]
    if not valid_tags:
        return [None] * len(tags), tags  # all invalid

    # Batch DB lookup
    placeholders = ",".join(["%s"] * len(valid_tags))
    query = f"""
        SELECT tag, guild
        FROM guild_tag_name
        WHERE LOWER(tag) IN ({placeholders})
        ORDER BY priority DESC
    """
    rows = await Database.fetch(query, tuple(t.lower() for t in valid_tags))

    # Pick highest-priority name for each tag
    for row in rows:
        t = row["tag"].lower()
        if t not in name_map:
            name_map[t] = row["guild"]

    # Fallback for missing
    db_identified = set(name_map.keys())
    missing = [t for t in valid_tags if t.lower() not in db_identified]

    if missing:
        fallback_results = await asyncio.gather(*(guild_name_from_tag(t) for t in missing))
        for tag, name in zip(missing, fallback_results):
            ltag = tag.lower()
            if name:
                name_map[ltag] = name
            else:
                unidentified.append(tag)

    # Rebuild final output list in input order (original casing preserved)
    final_names = []
    for tag in tags:
        ltag = tag.lower()
        name = name_map.get(ltag)
        final_names.append(name if name else None)
        if ltag not in name_map and tag not in unidentified:
            unidentified.append(tag)

    return final_names, unidentified




async def guild_tags_from_names(names: List[str]) -> Tuple[MutableSet[str], List[str]]:
    tag_map = {}
    unidentified = []

    # Clean input
    valid_names = [n for n in names if "-" not in n and ";" not in n]
    if not valid_names:
        return [None] * len(names), names # All names were invalid

    # Batch DB lookup
    placeholders = ",".join(["%s"] * len(valid_names))
    query = f"""
        SELECT guild, tag
        FROM guild_tag_name
        WHERE LOWER(guild) IN ({placeholders})
        ORDER BY priority DESC
    """
    rows = await Database.fetch(query, tuple(n.lower() for n in valid_names))

    # Pick highest-priority tag for each name
    for row in rows:
        gname = row["guild"].lower()
        if gname not in tag_map:
            tag_map[gname] = row["tag"]

    # Fallback for missing
    db_identified = set(tag_map.keys())
    missing = [n for n in valid_names if n.lower() not in db_identified]

    if missing:
        fallback_results = await asyncio.gather(*(guild_tag_from_name(n) for n in missing))
        for name, tag in zip(missing, fallback_results):
            lname = name.lower()
            if tag:
                tag_map[lname] = tag
            else:
                unidentified.append(name)


    # Rebuild final output list in input order (original casing preserved)
    final_tags = []
    for name in names:
        lname = name.lower()
        tag = tag_map.get(lname)
        final_tags.append(tag if tag else None)
        if lname not in tag_map and name not in unidentified:
            unidentified.append(name)

    return final_tags, unidentified



async def player_guild_from_uuid(uuid: str) -> str:
    result = await Database.fetch("SELECT joined FROM guild_join_log WHERE uuid=%s ORDER BY date DESC LIMIT 1", (uuid))
    guild = None if not result else result[0]["joined"]
    return guild

async def player_guilds_from_uuids(uuids: list[str]) -> dict[str, str]:
    if not uuids:
        return {}

    placeholders = ",".join(["%s"] * len(uuids))
    query = f"""
        SELECT uuid, joined
        FROM guild_join_log
        WHERE uuid IN ({placeholders})
        ORDER BY date DESC
    """
    rows = await Database.fetch(query, tuple(uuids))

    player_guilds = {}
    for row in rows:
        if row["uuid"] not in player_guilds:
            player_guilds[row["uuid"]] = row["joined"]

    return player_guilds
