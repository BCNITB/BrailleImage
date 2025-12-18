import logging
import sys

def setup_logging():
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    root_logger = logging.getLogger()

    # Log to file
    file_handler = logging.FileHandler("braille_converter.log")
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    # Log to console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    root_logger.setLevel(logging.INFO)
