from typing import Tuple


# Thresholds for war ranks, ascending order of required war counts
war_ranks = [0, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 20000]

# Thresholds for XP ranks, ascending order of required experience points
xp_ranks = [0, 100e6, 500e6, 1e9, 2.5e9, 5e9, 25e9, 50e9, 100e9, 250e9, 500e9]

# Roman numeral representation for ranks 0 through 10
numeral_map = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]



def get_war_rank(warcnt: int) -> Tuple[str, int]:
    """
    Get the war rank Roman numeral and next rank threshold for a given war count.

    Args:
        warcnt (int): The player's war count.

    Returns:
        Tuple[str, int]: Tuple containing the Roman numeral rank string and the next rank threshold.
                         The rank corresponds to the highest threshold not exceeding warcnt,
                         and the next threshold is the one that must be reached to rank up.
    """
    i = 0
    # Iterate over war ranks until warcnt is less than the threshold
    while i < len(war_ranks):
        if warcnt < war_ranks[i]:
            break
        i += 1

    # i-1 is the current rank index, i is the next rank index (clamped to max)
    return numeral_map[i-1], war_ranks[min(i, len(war_ranks)-1)]



def get_xp_rank(xp: int) -> Tuple[str, float]:
    """
    Get the XP rank Roman numeral and next rank threshold for a given XP amount.

    Args:
        xp (int): The player's total experience points.

    Returns:
        Tuple[str, float]: Tuple containing the Roman numeral rank string and the next XP threshold.
                           The rank corresponds to the highest threshold not exceeding xp,
                           and the next threshold is the one that must be reached to rank up.
    """
    i = 0
    # Iterate over xp ranks until xp is less than the threshold
    while i < len(xp_ranks):
        if xp < xp_ranks[i]:
            break
        i += 1

    # i-1 is the current rank index, i is the next rank index (clamped to max)
    return numeral_map[i-1], xp_ranks[min(i, len(xp_ranks)-1)]



def get_xp_rank_index(xp: int) -> int:
    """
    Get the index of the XP rank for a given XP amount.

    Args:
        xp (int): The player's total experience points.

    Returns:
        int: The rank index corresponding to the highest threshold not exceeding xp.
    """
    i = 0
    while i < len(xp_ranks):
        if xp < xp_ranks[i]:
            break
        i += 1
    return i



def get_war_rank_index(wars: int) -> int:
    """
    Get the index of the war rank for a given war count.

    Args:
        wars (int): The player's war count.

    Returns:
        int: The rank index corresponding to the highest threshold not exceeding wars.
    """
    i = 0
    while i < len(war_ranks):
        if wars < war_ranks[i]:
            break
        i += 1
    return i
