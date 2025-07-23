import time
from typing import Tuple, Union
import logging

from database.connection import Database 


async def get_range_from_season(season_name: str) -> Union[Tuple[float, float], None]:
    if '-' in season_name:
        return None

    res = await Database.fetch(
        "SELECT start_time, end_time FROM season_list WHERE season_name=%s LIMIT 1", 
        (season_name)
    )

    if not res:
        return None

    start_ts = res[0]["start_time"]
    end_ts = res[0]["end_time"]

    return start_ts, end_ts

async def get_range_from_string(range_input: str) -> Union[Tuple[float, float], None]:
    """
    Parses a string input into two UTC timestamps (left, right).
    
    Accepts:
    - "7" → from 7 days ago to now
    - "0,6" or "0, 6" → from 6 days ago to today
    - Season name (e.g., "season1") → uses DB lookup
    """
    now = time.time()
    range_input = range_input.strip()

    # Handle potential season name
    if ',' not in range_input and not range_input.replace('.', '', 1).isdigit():
        season_range = await get_range_from_season(range_input)
        if season_range is None:
            return None
        
        left, right = season_range
        return left, right

    try:
        # Parse number ranges
        parts = [p.strip() for p in range_input.split(',') if p.strip()]
        if len(parts) == 1:
            left_days = float(parts[0])
            right_days = 0.0
        elif len(parts) == 2:
            right_days = float(parts[0])
            left_days = float(parts[1])
        else:
            return None

        left = now - left_days * 86400
        right = now - right_days * 86400
        return left, right
    except ValueError:
        return None
