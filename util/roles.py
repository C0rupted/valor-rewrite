import discord
from core.config import config

def is_ANO_member(user: discord.User):
    roles = {x.id for x in user.roles}
    try:
        return True if config.ANO_MEMBER_ROLE in roles else False
    except AttributeError:
        return False


def is_ANO_military_member(user: discord.User):
    roles = {x.id for x in user.roles}
    try:
        return True if config.ANO_MEMBER_ROLE in roles else False
    except AttributeError:
        return False


def is_ANO_high_rank(user: discord.User):
    allowed_roles = config.ANO_HIGH_RANK_ROLES 
    roles = {x.id for x in user.roles}

    has_permission = False
    for role in roles:
        if role in allowed_roles:
            has_permission = True
        
    return has_permission

def is_ANO_titan_rank(user: discord.User):
    allowed_roles = config.ANO_TITAN_ROLES 
    roles = {x.id for x in user.roles}

    has_permission = False
    for role in roles:
        if role in allowed_roles:
            has_permission = True
        
    return has_permission

def is_ANO_chief(user: discord.User):
    allowed_roles = config.ANO_CHIEF_ROLES 
    roles = {x.id for x in user.roles}

    has_permission = False
    for role in roles:
        if role in allowed_roles:
            has_permission = True
        
    return has_permission