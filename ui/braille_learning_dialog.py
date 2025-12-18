from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QPushButton, QApplication, QScrollArea, QWidget, QComboBox
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
import braille_processor
from .braille_cell_widget import BrailleCellWidget
from .braille_cell_editor import BrailleCellEditor

class BrailleLearningDialog(QDialog):
    def __init__(self, current_language, braille_dots_mode, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Modo de Aprendizaje de Braille"))
        self.setGeometry(200, 200, 800, 600)

        self.language_map = {
            "Español": "spanish",
            "Catalán": "catalan",
            "Euskera": "euskera",
            "Gallego": "galician"
        }
        self.current_language = current_language
        self.braille_dots_mode = braille_dots_mode
        self.current_mode = 'tinta_a_braille'  # or 'braille_a_tinta'

        self.init_ui()
        self.update_mode_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Top layout for mode switch and language selection
        top_layout = QHBoxLayout()

        self.switch_mode_button = QPushButton(self.tr("Cambiar a modo Braille a Tinta"))
        self.switch_mode_button.clicked.connect(self.switch_mode)
        top_layout.addWidget(self.switch_mode_button)

        self.language_combo = QComboBox()
        self.language_combo.addItems(self.language_map.keys())
        # Set initial value
        for lang_text, lang_id in self.language_map.items():
            if lang_id == self.current_language:
                self.language_combo.setCurrentText(lang_text)
                break
        self.language_combo.currentTextChanged.connect(self.language_changed)
        top_layout.addWidget(self.language_combo)

        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # Input Text Area
        self.input_label = QLabel(self.tr("Escribe aquí (texto en tinta):"))
        main_layout.addWidget(self.input_label)

        self.input_text_edit = QTextEdit()
        self.input_text_edit.setFont(QFont("Arial", 12))
        self.input_text_edit.textChanged.connect(self.update_braille_output)
        main_layout.addWidget(self.input_text_edit)

        # Braille Output Area
        self.braille_label = QLabel(self.tr("Representación Braille:"))
        main_layout.addWidget(self.braille_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area_widget_contents = QWidget()
        self.braille_cells_layout = QHBoxLayout(self.scroll_area_widget_contents)
        self.braille_cells_layout.setAlignment(Qt.AlignLeft)
        self.scroll_area.setWidget(self.scroll_area_widget_contents)
        main_layout.addWidget(self.scroll_area)

        # Add Braille Character Button
        self.add_braille_char_button = QPushButton(self.tr("Añadir Carácter Braille"))
        self.add_braille_char_button.clicked.connect(self.add_braille_character)
        main_layout.addWidget(self.add_braille_char_button)

        # Feedback Area
        self.feedback_label = QLabel(self.tr("Información del carácter Braille:"))
        self.feedback_label.setWordWrap(True)
        main_layout.addWidget(self.feedback_label)

        # Close Button
        self.close_button = QPushButton(self.tr("Cerrar"))
        self.close_button.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def language_changed(self, lang_text):
        self.current_language = self.language_map.get(lang_text, 'spanish')
        if self.current_mode == 'tinta_a_braille':
            self.update_braille_output()
        else:
            self.update_plain_text_output()

    def switch_mode(self):
        if self.current_mode == 'tinta_a_braille':
            self.current_mode = 'braille_a_tinta'
        else:
            self.current_mode = 'tinta_a_braille'
        self.update_mode_ui()

    def update_mode_ui(self):
        if self.current_mode == 'tinta_a_braille':
            self.switch_mode_button.setText(self.tr("Cambiar a modo Braille a Tinta"))
            self.input_label.setText(self.tr("Escribe aquí (texto en tinta):"))
            self.input_text_edit.setReadOnly(False)
            self.add_braille_char_button.hide()
            self.input_text_edit.textChanged.connect(self.update_braille_output)
            try:
                self.input_text_edit.textChanged.disconnect(self.update_plain_text_output)
            except (TypeError, RuntimeError):
                pass
        else: # braille_a_tinta
            self.switch_mode_button.setText(self.tr("Cambiar a modo Tinta a Braille"))
            self.input_label.setText(self.tr("Salida de texto en tinta:"))
            self.input_text_edit.setReadOnly(True)
            self.add_braille_char_button.show()
            try:
                self.input_text_edit.textChanged.disconnect(self.update_braille_output)
            except (TypeError, RuntimeError):
                pass

    def add_braille_character(self):
        editor = BrailleCellEditor(self.braille_dots_mode, self)
        if editor.exec():
            braille_char = editor.get_braille_char()
            cell_widget = BrailleCellWidget(braille_char)
            self.braille_cells_layout.addWidget(cell_widget)
            self.update_plain_text_output()

    def get_braille_string(self):
        braille_string = ""
        for i in range(self.braille_cells_layout.count()):
            widget = self.braille_cells_layout.itemAt(i).widget()
            if isinstance(widget, BrailleCellWidget):
                braille_string += widget.braille_char
        return braille_string

    def update_plain_text_output(self):
        braille_text = self.get_braille_string()
        plain_text = braille_processor.convert_braille_to_text(
            braille_text, self.current_language, self.braille_dots_mode
        )
        self.input_text_edit.setText(plain_text)

        if braille_text:
            last_char = braille_text[-1]
            info = braille_processor.get_braille_info(last_char)
            if info:
                feedback_text = f"<b>{info['desc']}</b><br>"
                feedback_text += f"Carácter: {info['char']}<br>"
                feedback_text += f"Puntos: {info['dots']}"
                self.feedback_label.setText(feedback_text)
            else:
                self.feedback_label.setText(self.tr("Información del carácter Braille:"))
        else:
            self.feedback_label.setText(self.tr("Información del carácter Braille:"))

    def update_braille_output(self):
        # Clear previous cells
        for i in reversed(range(self.braille_cells_layout.count())):
            self.braille_cells_layout.itemAt(i).widget().setParent(None)

        plain_text = self.input_text_edit.toPlainText()
        if plain_text:
            braille_text = braille_processor.convert_text_to_braille(
                plain_text, self.current_language, self.braille_dots_mode
            )
            for char in braille_text:
                cell_widget = BrailleCellWidget(char)
                self.braille_cells_layout.addWidget(cell_widget)

            if braille_text:
                last_char = braille_text[-1]
                info = braille_processor.get_braille_info(last_char)
                if info:
                    feedback_text = f"<b>{info['desc']}</b><br>"
                    feedback_text += f"Carácter: {info['char']}<br>"
                    feedback_text += f"Puntos: {info['dots']}"
                    self.feedback_label.setText(feedback_text)
                else:
                    self.feedback_label.setText(self.tr("Información del carácter Braille:"))
        else:
            self.feedback_label.setText(self.tr("Información del carácter Braille:"))

    def retranslate_ui(self):
        self.setWindowTitle(self.tr("Modo de Aprendizaje de Braille"))
        if self.current_mode == 'tinta_a_braille':
            self.switch_mode_button.setText(self.tr("Cambiar a modo Braille a Tinta"))
            self.input_label.setText(self.tr("Escribe aquí (texto en tinta):"))
        else:
            self.switch_mode_button.setText(self.tr("Cambiar a modo Tinta a Braille"))
            self.input_label.setText(self.tr("Salida de texto en tinta:"))
        self.braille_label.setText(self.tr("Representación Braille:"))
        self.add_braille_char_button.setText(self.tr("Añadir Carácter Braille"))
        self.feedback_label.setText(self.tr("Información del carácter Braille:"))
        self.close_button.setText(self.tr("Cerrar"))


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    # The BrailleCellWidget needs to be imported for the dialog to work
    # This is a workaround for the standalone execution of the script
    try:
        from braille_cell_widget import BrailleCellWidget
    except ImportError:
        print("BrailleCellWidget not found. Please run from the main application.")
        sys.exit(1)

    dialog = BrailleLearningDialog('spanish', 6)
    dialog.show()
    sys.exit(app.exec())