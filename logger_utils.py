import logging
import sys
import configparser

def get_logger(name="ATMLogger"):
    """Create a logger using config.ini parameters."""
    config = configparser.ConfigParser()
    config.read("config.ini")

    logfile = config.get("logging", "logfile", fallback="bank_server.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid adding multiple handlers
    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(logfile)
        fh.setLevel(logging.INFO)

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


def log_info(message):
    get_logger().info(message)

def log_error(message):
    get_logger().error(message)
