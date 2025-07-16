import discord
from core.config import config

def is_ANO_member(user: discord.User):
    roles = {x.id for x in user.roles}
    try:
        return True if config.ANO_MEMBER_ROLE in roles else False
    except AttributeError:
        return False