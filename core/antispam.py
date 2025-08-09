import discord, time

from discord import app_commands
from collections import defaultdict, deque


# Max number of allowed calls per user per minute
MAX_CALLS_PER_MINUTE = 10

# Duration for which a user is locked out after exceeding the limit (in seconds)
LOCK_DURATION = 180  # 3 minutes

# Tracks timestamps of recent command calls per user (deque to keep last 11 timestamps)
command_usage = defaultdict(lambda: deque(maxlen=11))

# List of users currently locked out from using commands
locked_users = []

# Maps user_id to the lock expiry timestamp
lock_expiry = {}


class RateLimitExceeded(app_commands.CheckFailure):
    """Custom exception raised when a user exceeds rate limits."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def rate_limit_check():
    """Decorator factory for Discord app commands that rate-limits usage per user."""
    
    def predicate(interaction: discord.Interaction) -> bool:
        user_id = interaction.user.id
        now = time.time()

        # Unlock user if lock has expired
        if user_id in lock_expiry and now > lock_expiry[user_id]:
            locked_users.remove(user_id)
            del lock_expiry[user_id]

        # If user is locked, raise error with remaining lock time
        if user_id in locked_users:
            remaining = int(lock_expiry[user_id] - now)
            minutes, seconds = divmod(remaining, 60)
            formatted = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
            raise RateLimitExceeded(
                f"You're currently locked out due to too many commands. Try again in {formatted}."
            )

        # Record current command usage timestamp for user
        usage = command_usage[user_id]
        usage.append(now)

        # Clean up timestamps older than 1 hour
        while usage and now - usage[0] > 3600:
            usage.popleft()

        # Count how many calls were made in the last 60 seconds
        calls_last_minute = [t for t in usage if now - t <= 60]

        # If user exceeded max calls per minute, lock them out
        if len(calls_last_minute) > MAX_CALLS_PER_MINUTE:
            locked_users.append(user_id)
            lock_expiry[user_id] = now + LOCK_DURATION
            raise RateLimitExceeded(
                f"Too many commands — you've been locked out for {LOCK_DURATION // 60} minutes."
            )

        return True

    return app_commands.check(predicate)
