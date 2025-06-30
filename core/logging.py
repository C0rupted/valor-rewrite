import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Create a null handler to prevent output to the console
    logging.getLogger('discord').addHandler(logging.NullHandler())

