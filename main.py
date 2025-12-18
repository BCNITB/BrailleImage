import sys
import logging
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from logger_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    logging.info("Iniciando la aplicación Braille Converter...")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        logging.info("Aplicación cerrada por el usuario.")
        pass
