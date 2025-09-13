import discord, logging
from core.config import config


def _has_role(user_roles: list[discord.Role], allowed_roles) -> bool:
    """
    Internal helper to check if any role in `user_roles` matches `allowed_roles`.

    Args:
        user_roles (list[discord.Role]): List of roles belonging to the user.
        allowed_roles (list[int] | int): A role ID or list of role IDs that grant permission.

    Returns:
        bool: True if the user has at least one of the allowed roles, False otherwise.
    """
    # In testing mode, bypass all role checks to avoid blocking during dev
    if config.TESTING:
        return True

    # Convert user_roles to a set of IDs and check for intersection
    user_role_ids = {role.id for role in user_roles}
    return not user_role_ids.isdisjoint(allowed_roles)


def is_ANO_member(user_roles: list[discord.Role]) -> bool:
    """Check if the user is an ANO member."""
    return _has_role(user_roles, config.ANO_MEMBER_ROLES)


def is_ANO_military_member(user_roles: list[discord.Role]) -> bool:
    """Check if the user is an ANO military member."""
    return _has_role(user_roles, config.ANO_MILITARY_ROLES)


def is_ANO_high_rank(user_roles: list[discord.Role]) -> bool:
    """Check if the user has a high rank in ANO."""
    return _has_role(user_roles, config.ANO_HIGH_RANK_ROLES)


def is_ANO_titan_rank(user_roles: list[discord.Role]) -> bool:
    """Check if the user is Titan rank or higher in ANO."""
    return _has_role(user_roles, config.ANO_TITAN_ROLES)


def is_ANO_chief(user_roles: list[discord.Role]) -> bool:
    """Check if the user is a Chief in ANO."""
    return _has_role(user_roles, config.ANO_CHIEF_ROLES)
