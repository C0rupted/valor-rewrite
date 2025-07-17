import os, time
from core.bot import run_bot

if __name__ == "__main__":
    # Set to GMT time
    os.environ["TZ"] = "Europe/London"
    time.tzset()


    # Create these directories if they don't already exist
    directories = ["storages"]
    for dir in directories:
        try:
            os.makedirs(dir, exist_ok=True)
        except OSError as e:
            print(f"Error creating directory '{dir}': {e}")
    
    # Run bot
    run_bot()
