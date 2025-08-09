import logging


class ValorLogFormatter(logging.Formatter):
    # ANSI escape codes for colors and text styles
    CODES = {
        'INFO':     '\033[92m',   # Bright Green
        'WARNING':  '\033[93m',   # Bright Yellow
        'ERROR':    '\033[91m',   # Bright Red
        'CRITICAL': '\033[95m',   # Bright Magenta
        'GRAY':     '\033[90m',   # Dark Grey
        'BOLD':     '\033[1m',    # Bold text
        'ITALIC':   '\033[3m',    # Italic text

        'RESET':    '\033[0m',    # Reset all formatting
    }

    # Fixed width for level tag strings (like "[INFO]     ") for alignment
    TAG_WIDTH = 10

    def format(self, record):
        # Create a padded log level tag string, e.g. "[INFO]     "
        padded_tag = f"[{record.levelname}]".ljust(self.TAG_WIDTH)

        # Get color code for the log level, default to empty if not found
        color = self.CODES.get(record.levelname, '')

        reset = self.CODES["RESET"]
        gray = self.CODES["GRAY"]
        bold = self.CODES["BOLD"]

        # Format the timestamp using the formatter's datefmt
        timestamp = self.formatTime(record, self.datefmt)

        # Build and return the final colored log line string
        # Format: bold + color + level_tag + reset + gray + timestamp + reset + "  -   " + message
        return f"{bold}{color}{padded_tag}{reset}{gray} {timestamp}{reset}  -   {record.getMessage()}"


def setup_logging():
    # Create a stream handler (logs to stdout)
    handler = logging.StreamHandler()

    # Set our custom formatter with desired timestamp format
    handler.setFormatter(ValorLogFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    # Configure root logger with INFO level and our handler
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler]
    )
