import os
from core.bot import run_bot

if __name__ == "__main__":
    directories = ["storages"]
    for dir in directories:
        try:
            os.makedirs(dir, exist_ok=True)
        except OSError as e:
            print(f"Error creating directory '{dir}': {e}")
    
    run_bot()
