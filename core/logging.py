import logging

class ValorLogFormatter(logging.Formatter):
    CODES = {
        'INFO':     '\033[92m',   # Bright Green
        'WARNING':  '\033[93m',   # Bright Yellow
        'ERROR':    '\033[91m',   # Bright Red
        'CRITICAL': '\033[95m',   # Bright Magenta
        'GRAY':     '\033[90m',   # Dark grey
        'BOLD':     '\033[1m',    # Bold
        'ITALIC':   '\033[3m',    # Italic

        'RESET':    '\033[0m',    # Reset
    }

    # Longest full tag: [CRITICAL] = 10 chars
    TAG_WIDTH = 10

    def format(self, record):
        padded_tag = f"[{record.levelname}]".ljust(self.TAG_WIDTH)
        color = self.CODES.get(record.levelname, '')

        reset = self.CODES["RESET"]
        gray = self.CODES["GRAY"]
        bold = self.CODES["BOLD"]

        timestamp = self.formatTime(record, self.datefmt)
        return f"{bold}{color}{padded_tag}{reset}{gray} {timestamp}{reset}  -   {record.getMessage()}" # [INFO]     XXXX-XX-XX xx:xx:xx - test


def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(ValorLogFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler]
    )
