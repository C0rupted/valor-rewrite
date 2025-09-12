import discord, logging
from core.config import config



def _has_role(user: discord.User, allowed_roles) -> bool:
    """
    Internal helper to check if a user has any role from `allowed_roles`.

    Args:
        user (discord.User or discord.Member): The user whose roles to check.
        allowed_roles (list[int] | int): A role ID or a set of role IDs that grant permission.

    Returns:
        bool: True if the user has at least one of the allowed roles, False otherwise.
    """
    if config.TESTING: # Always return True in testing mode to avoid permission issues
        logging.info("Testing mode active; skipping role check.")
        return True
    
    try:
        user_roles = {role.id for role in user.roles}  # Extract role IDs
    except AttributeError:
        return False  # In case `user` has no `.roles` (not a discord.Member object)

    # Ensure allowed_roles is a set for easy comparison
    if not isinstance(allowed_roles, list):
        allowed_roles = {allowed_roles}

    # Intersection check — returns True if there's any overlap
    return not user_roles.isdisjoint(allowed_roles)



def is_ANO_member(user: discord.User) -> bool:
    """Check if the user is an ANO member."""
    logging.info(f"Checking ANO member status for user {user} with roles: {[role.id for role in getattr(user, 'roles', [])]}")
    return _has_role(user, config.ANO_MEMBER_ROLE)


def is_ANO_military_member(user: discord.User) -> bool:
    """Check if the user is an ANO military member."""
    logging.info(f"Checking ANO military member status for user {user} with roles: {[role.id for role in getattr(user, 'roles', [])]}")
    return _has_role(user, config.ANO_MILITARY_ROLE)


def is_ANO_high_rank(user: discord.User) -> bool:
    """Check if the user has a high rank in ANO."""
    logging.info(f"Checking ANO high rank status for user {user} with roles: {[role.id for role in getattr(user, 'roles', [])]}")
    return _has_role(user, config.ANO_HIGH_RANK_ROLES)


def is_ANO_titan_rank(user: discord.User) -> bool:
    """Check if the user is Titan rank or higher in ANO."""
    logging.info(f"Checking ANO titan rank status for user {user} with roles: {[role.id for role in getattr(user, 'roles', [])]}")
    return _has_role(user, config.ANO_TITAN_ROLES)


def is_ANO_chief(user: discord.User) -> bool:
    """Check if the user is a Chief in ANO."""
    logging.info(f"Checking ANO chief status for user {user} with roles: {[role.id for role in getattr(user, 'roles', [])]}")
    return _has_role(user, config.ANO_CHIEF_ROLES)

