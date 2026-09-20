import logging
import sys


class ColorFormatter(logging.Formatter):
    """Custom formatter to add colors to standard Python logging."""

    # ANSI escape color codes
    GREY = "\x1b[38;20m"
    CYAN = "\x1b[36;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    # Log format structure
    format_str = "%(asctime)s | %(levelname)-8s | %(message)s"

    FORMATS = {
        logging.DEBUG: CYAN + format_str + RESET,
        logging.INFO: GREEN + format_str + RESET,
        logging.WARNING: YELLOW + format_str + RESET,
        logging.ERROR: RED + format_str + RESET,
        logging.CRITICAL: BOLD_RED + format_str + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.format_str)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)


def get_logger(name="SecuritySystem"):
    """Initializes and returns a colored logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate log entries if called multiple times
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ColorFormatter())
        logger.addHandler(console_handler)

    return logger


# Export a default global logger
logger = get_logger()
