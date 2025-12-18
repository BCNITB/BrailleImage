import logging
from functools import wraps
from PySide6.QtWidgets import QMessageBox

class BrailleConversionError(Exception):
    """Custom exception for errors during Braille conversion."""
    pass

class FileProcessingError(Exception):
    """Custom exception for errors during file processing."""
    pass

class ImageProcessingError(Exception):
    """Custom exception for errors during image processing."""
    pass

def log_error(message, exc_info=False):
    """Logs an error message."""
    logging.error(message, exc_info=exc_info)

def gui_error_handler(func):
    """
    A decorator that wraps a function in a try-except block to catch
    specific custom exceptions and display a user-friendly QMessageBox.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (BrailleConversionError, FileProcessingError, ImageProcessingError) as e:
            log_error(f"An error occurred in {func.__name__}: {e}")
            QMessageBox.critical(self, "Error", str(e))
        except Exception as e:
            log_error(f"An unexpected error occurred in {func.__name__}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error Inesperado",
                                 f"Ha ocurrido un error inesperado: {e}\n\n"
                                 "Consulte el archivo de registro (braille_converter.log) para más detalles.")
    return wrapper
