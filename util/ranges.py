import time
from typing import Tuple, Union

from database import Database 



class RangeTooLargeError(Exception):
    """Raised when the requested range exceeds the maximum allowed days."""
    pass



async def get_range_from_season(season_name: str) -> Union[Tuple[float, float], None]:
    """
    Retrieves the start and end timestamps for a given season name from the database.

    Args:
        season_name (str): The name of the season.

    Returns:
        Tuple[float, float] | None: The (start_time, end_time) in UNIX timestamps if found, else None.
    """
    # Season names with '-' are invalid or special cases, skip
    if '-' in season_name:
        return None

    # Query the season_list table for matching season_name
    res = await Database.fetch(
        "SELECT start_time, end_time FROM season_list WHERE season_name=%s LIMIT 1", 
        (season_name,)
    )

    # Return None if no matching season found
    if not res:
        return None

    start_ts = res[0]["start_time"]
    end_ts = res[0]["end_time"]

    return start_ts, end_ts



async def get_range_from_string(range_input: str, max_allowed_range: int = 50) -> Union[Tuple[float, float], None]:
    """
    Parses a string representing a time range into two UTC timestamps (left, right).

    Accepts inputs in several formats:
    - Single number: "7" means from 7 days ago to now.
    - Two comma-separated numbers: "0,6" or "0, 6" means from 6 days ago to today.
    - Season name (e.g. "season1") which will be looked up from the database.

    Args:
        range_input (str): The input range string.
        max_allowed_range (int): Maximum allowed range in days (default 50).

    Raises:
        RangeTooLargeError: If the parsed range exceeds max_allowed_range.

    Returns:
        Tuple[float, float] | None: Tuple of (left_timestamp, right_timestamp) if parsed successfully, else None.
    """
    now = time.time()
    range_input = range_input.strip()

    # If input does not contain a comma and isn't numeric, treat it as a season name
    if ',' not in range_input and not range_input.replace('.', '', 1).isdigit():
        season_range = await get_range_from_season(range_input)
        if season_range is None:
            return None

        left, right = season_range
    else:
        try:
            # Split input by comma, strip whitespace
            parts = [p.strip() for p in range_input.split(',') if p.strip()]

            # Parse input accordingly
            if len(parts) == 1:
                left_days = float(parts[0])
                right_days = 0.0  # default to now
            elif len(parts) == 2:
                right_days = float(parts[0])
                left_days = float(parts[1])
            else:
                # Invalid format (more than two parts)
                return None

            # Convert days ago to timestamps
            left = now - left_days * 86400
            right = now - right_days * 86400
        except ValueError:
            # Failed to parse floats
            return None

    # Check if range is within allowed maximum range
    delta_days = abs(right - left) / 86400
    if max_allowed_range:
        if delta_days > max_allowed_range:
            raise RangeTooLargeError(f"Range exceeds the allowed limit of {max_allowed_range} days.")

    return left, right



def range_alt(_range: int):
    """
    Simple wrapper for Python's built-in range function.

    Used in commands that have a range argument as an alternate of range.

    Args:
        _range (int): The range limit.

    Returns:
        range: Python range object from 0 to _range-1.
    """
    return range(_range)



async def get_current_season() -> str | None:
    """
    Returns the current active season name from the database.

    The query excludes the 'all' season by fetching up to two results and
    returning the second, which should be the actual current season.

    Returns:
        str | None: The current season name if active, else None.
    """
    current_ts = int(time.time())

    # Query seasons active at current timestamp
    query = """
        SELECT season_name
        FROM season_list
        WHERE start_time <= %s AND end_time >= %s
        LIMIT 2
    """

    rows = await Database.fetch(query, (current_ts, current_ts))
    if not rows:
        return None  # No active season

    try:
        # The first result is 'all' season, return the second which is the actual season
        return rows[1]["season_name"]
    except IndexError:
        # If only one result (likely 'all'), return None as no active season found
        return None


