import math



def human_format(number):
    """
    Formats a large number into a human-readable string using metric suffixes.

    Examples:
        123       -> "123"
        1234      -> "1.234K"
        1234567   -> "1.235M"
        1234567890-> "1.235B"

    Args:
        number (int or float): The number to format.

    Returns:
        str: Human-readable string with suffix (K, M, B, T) or '' for small numbers.

    Notes:
        - Uses base 1000 for suffix scaling.
        - If number is zero or None, returns "0".
        - Rounds to up to 3 decimal places if not an integer after scaling.
    """
    units = ['', 'K', 'M', 'B', 'T']  # Suffixes for thousands, millions, etc.
    k = 1000.0  # Base for scaling

    if not number:
        # Handles 0, None, False as zero
        number = 0

    try:
        # Calculate magnitude (power of 1000)
        # Adding a small epsilon (1e-8) to avoid math domain errors with log(0)
        magnitude = int(math.floor(math.log(number + 1e-8, k)))

        # Scale number down to [1, 1000) range for suffix usage
        x = number / (k ** magnitude)

        # If x is an integer, format as int; else round to 3 decimals
        v = int(x) if int(x) == x else round(x, 3)

        # Combine scaled number with appropriate suffix
        return f"{v}{units[magnitude]}"
    except ValueError:
        # In case of math domain error or other issues, return "0"
        return "0"


