from database.connection import Database
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
    
    guilds = await Database.fetch(f"SELECT * FROM guild_tag_name WHERE LOWER(guild)='{name.lower()}' ORDER BY priority DESC")
    
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



async def guild_names_from_tags(tags: List[str]) -> Tuple[MutableSet[str], List[str]]:
    unidentified = []
    guild_names = []
    guild_names_list = [await guild_name_from_tag(x) for x in tags]
    for i in range(len(tags)):
        if not guild_names_list[i]: unidentified.append(tags[i])
        else: guild_names.append(guild_names_list[i])
    
    return guild_names, unidentified



async def guild_tags_from_names(names: List[str]) -> Tuple[MutableSet[str], List[str]]:
    unidentified = []
    guild_tags = []
    guild_tags_list = [await guild_tag_from_name(x) for x in names]
    for i in range(len(names)):
        if not guild_tags_list[i]: unidentified.append(names[i])
        else: guild_tags.append(guild_tags_list[i])
    
    return guild_tags, unidentified


