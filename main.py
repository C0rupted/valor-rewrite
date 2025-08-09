import os, time
from core.bot import run_bot


if __name__ == "__main__":
    """
    Main entry point for starting the Discord bot.

    This script:
    1. Sets the process timezone to GMT (Europe/London).
    2. Ensures necessary storage directories exist.
    3. Starts the bot using the `run_bot` function from `core.bot`.

    Execution:
        python main.py
    """

    # Timzeone is critical for all time-related operations,this maintains consistency across all testing environments.
    os.environ["TZ"] = "Europe/London"
    time.tzset()  # Apply the timezone change to the current process


    # These directories store data and settings as well as other persistent data.
    directories = [
        "storages",                  # Root storage folder
        "storages/user_settings",    # Per-user configuration/settings
        "storages/guild_settings"    # Per-guild configuration/settings
    ]

    # Create directories
    for dir_path in directories:
        try:
            # Create the directory if it doesn't already exist.
            os.makedirs(dir_path, exist_ok=True)
        except OSError as e:
            # Log an error if directory creation fails.
            print(f"Error creating directory '{dir_path}': {e}")


    # Start the bot's event loop and connects it to Discord.
    run_bot()
