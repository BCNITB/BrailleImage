from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel,
    QSpinBox, QDialogButtonBox, QWidget, QFormLayout, QApplication, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, Signal
import win32print

class BraillePrinterDialog(QDialog):
    def __init__(self, current_dots_mode, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Configuración de Impresora Braille"))
        self.setModal(True)

        self.main_layout = QVBoxLayout(self)

        self.settings_widget = QWidget()
        self.settings_layout = QFormLayout(self.settings_widget)

        # Printer Selection
        self.printer_label = QLabel(self.tr("Impresora:"))
        self.printer_combo = QComboBox()
        self.printer_combo.setAccessibleName(self.tr("Seleccionar impresora Braille"))
        self.printer_combo.setAccessibleDescription(self.tr("Elige la impresora Braille a la que enviar el texto."))
        self.settings_layout.addRow(self.printer_label, self.printer_combo)
        self._populate_printers() # Populate the combo box

        # Braille Dots Mode
        self.dots_mode_label = QLabel(self.tr("Modo de Puntos:"))
        self.dots_mode_combo = QComboBox()
        self.dots_mode_combo.addItem(self.tr("6 Puntos"), 6)
        self.dots_mode_combo.addItem(self.tr("8 Puntos"), 8)
        self.dots_mode_combo.setCurrentIndex(0 if current_dots_mode == 6 else 1)
        self.dots_mode_combo.setAccessibleName(self.tr("Seleccionar modo de puntos Braille"))
        self.settings_layout.addRow(self.dots_mode_label, self.dots_mode_combo)

        # Paper Size (Example options)
        self.paper_size_label = QLabel(self.tr("Tamaño de Papel:"))
        self.paper_size_combo = QComboBox()
        self.paper_size_combo.addItem(self.tr("Carta (8.5 x 11 in)"))
        self.paper_size_combo.addItem(self.tr("A4 (210 x 297 mm)"))
        self.paper_size_combo.addItem(self.tr("Personalizado..."))
        self.paper_size_combo.setAccessibleName(self.tr("Seleccionar tamaño de papel"))
        self.settings_layout.addRow(self.paper_size_label, self.paper_size_combo)

        # Interpoint (Yes/No)
        self.interpoint_label = QLabel(self.tr("Interpunto (Doble Cara):"))
        self.interpoint_combo = QComboBox()
        self.interpoint_combo.addItem(self.tr("No"))
        self.interpoint_combo.addItem(self.tr("Sí"))
        self.interpoint_combo.setAccessibleName(self.tr("Seleccionar interpunto (impresión a doble cara)"))
        self.settings_layout.addRow(self.interpoint_label, self.interpoint_combo)

        # Lines per page
        self.lines_per_page_label = QLabel(self.tr("Líneas por Página:"))
        self.lines_per_page_spinbox = QSpinBox()
        self.lines_per_page_spinbox.setRange(1, 100)
        self.lines_per_page_spinbox.setValue(25) # Common default
        self.lines_per_page_spinbox.setAccessibleName(self.tr("Número de líneas por página"))
        self.settings_layout.addRow(self.lines_per_page_label, self.lines_per_page_spinbox)

        # Characters per line
        self.chars_per_line_label = QLabel(self.tr("Caracteres por Línea:"))
        self.chars_per_line_spinbox = QSpinBox()
        self.chars_per_line_spinbox.setRange(1, 80)
        self.chars_per_line_spinbox.setValue(40) # Common default
        self.chars_per_line_spinbox.setAccessibleName(self.tr("Número de caracteres por línea"))
        self.settings_layout.addRow(self.chars_per_line_label, self.chars_per_line_spinbox)

        # Output Format
        self.output_format_label = QLabel(self.tr("Formato de Salida:"))
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItem(self.tr("Braille Unicode (.txt)"), "unicode_txt")
        self.output_format_combo.addItem(self.tr("BRF (.brf)"), "brf")
        self.output_format_combo.setAccessibleName(self.tr("Seleccionar formato de salida para la impresión"))
        self.settings_layout.addRow(self.output_format_label, self.output_format_combo)

        self.main_layout.addWidget(self.settings_widget)

        # Test Print Button
        self.test_print_button = QPushButton(self.tr("Imprimir Prueba"))
        self.test_print_button.setAccessibleName(self.tr("Botón de impresión de prueba"))
        self.test_print_button.setToolTip(self.tr("Envía una pequeña prueba a la impresora para verificar la conexión."))
        self.test_print_button.clicked.connect(self.test_print)
        self.main_layout.addWidget(self.test_print_button)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Print | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.main_layout.addWidget(self.button_box)

    def _populate_printers(self):
        try:
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            default_printer = win32print.GetDefaultPrinter()
            
            printer_names = [printer[2] for printer in printers]
            
            if not printer_names:
                QMessageBox.warning(self, self.tr("No se encontraron impresoras"), self.tr("No se encontraron impresoras instaladas en el sistema."))
                return

            self.printer_combo.addItems(printer_names)
            
            # Set default printer as selected
            if default_printer in printer_names:
                self.printer_combo.setCurrentText(default_printer)

        except Exception as e:
            QMessageBox.critical(self, self.tr("Error al listar impresoras"), self.tr(f"No se pudieron listar las impresoras: {e}"))

    def test_print(self):
        # This is a placeholder for actual test print logic
        QMessageBox.information(self, self.tr("Imprimir Prueba"), self.tr("Funcionalidad de impresión de prueba no implementada aún."))

    def get_settings(self):
        return {
            "printer_name": self.printer_combo.currentText(),
            "dots_mode": self.dots_mode_combo.currentData(),
            "paper_size": self.paper_size_combo.currentText(),
            "interpoint": self.interpoint_combo.currentIndex() == 1,
            "lines_per_page": self.lines_per_page_spinbox.value(),
            "chars_per_line": self.chars_per_line_spinbox.value(),
            "output_format": self.output_format_combo.currentData(),
        }

    def tr(self, text):
        return QApplication.translate("BraillePrinterDialog", text)
