from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QScrollArea,
    QSizePolicy
)
from PySide6.QtGui import QPainter, QColor, QFontMetrics, QFont
from PySide6.QtCore import Qt, Signal, QSize, QRect
from ui.braille_cell_editor import BrailleCellEditor
import braille_processor
import logging

# Re-defining DOT_POSITIONS here for clarity, or importing from a common utility.
# For now, let's define it here. It should eventually be in a shared utility.
DOT_POSITIONS = {
    1: (0, 0), 2: (1, 0), 3: (2, 0), 7: (3, 0),
    4: (0, 1), 5: (1, 1), 6: (2, 1), 8: (3, 1),
}


class BrailleTextEditor(QWidget):
    text_changed = Signal(str)

    def __init__(self, braille_text, language, dots_mode, parent=None):
        super().__init__(parent)
        self.language = language
        self.dots_mode = dots_mode
        self.current_braille_text = list(braille_text) if braille_text else [] # Store as list of characters
        self.current_index = 0 # Cursor position for editing

        self.setWindowTitle(self.tr("Editor de Texto Braille"))
        self.setAccessibleName(self.tr("Editor de Texto Braille Avanzado"))
        self.setAccessibleDescription(self.tr("Permite editar el texto Braille carácter por carácter e insertar nuevos caracteres."))

        self.main_layout = QVBoxLayout(self)

        # Braille text display area
        self.braille_display_edit = QTextEdit()
        self.braille_display_edit.setReadOnly(True)
        self.braille_display_edit.setFont(QFont("Courier New", 12))
        self.braille_display_edit.setAccessibleName(self.tr("Texto Braille Completo"))
        self.braille_display_edit.setAccessibleDescription(self.tr("Muestra el texto Braille en su totalidad. Utiliza los botones o teclas para navegar y editar."))
        self.main_layout.addWidget(self.braille_display_edit)
        
        # Controls for navigation and editing
        self.controls_layout = QHBoxLayout()

        self.btn_prev = QPushButton(self.tr("< Anterior"))
        self.btn_prev.setAccessibleName(self.tr("Carácter anterior"))
        self.btn_prev.clicked.connect(self.move_prev_char)
        self.controls_layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton(self.tr("Siguiente >"))
        self.btn_next.setAccessibleName(self.tr("Carácter siguiente"))
        self.btn_next.clicked.connect(self.move_next_char)
        self.controls_layout.addWidget(self.btn_next)

        self.btn_insert = QPushButton(self.tr("Insertar"))
        self.btn_insert.setAccessibleName(self.tr("Insertar carácter Braille"))
        self.btn_insert.clicked.connect(self.insert_char)
        self.controls_layout.addWidget(self.btn_insert)

        self.btn_delete = QPushButton(self.tr("Eliminar"))
        self.btn_delete.setAccessibleName(self.tr("Eliminar carácter Braille"))
        self.btn_delete.clicked.connect(self.delete_char)
        self.controls_layout.addWidget(self.btn_delete)

        self.main_layout.addLayout(self.controls_layout)

        # Single Braille cell editor
        self.cell_editor = BrailleCellEditor(self)
        self.cell_editor.dot_pattern_changed.connect(self.update_current_braille_char)
        self.main_layout.addWidget(self.cell_editor)

        self.update_ui()

    def tr(self, text):
        return QApplication.translate("BrailleTextEditor", text)

    def update_ui(self):
        # Update the full Braille text display
        self.braille_display_edit.setText("".join(self.current_braille_text))
        
        # Highlight the current character (basic implementation for now)
        # More advanced highlighting would involve HTML in QTextEdit or a custom painter
        
        # Update the single cell editor
        if self.current_braille_text and 0 <= self.current_index < len(self.current_braille_text):
            current_char = self.current_braille_text[self.current_index]
            bitmask = braille_processor.braille_char_to_bitmask(current_char)
            self.cell_editor.set_bitmask(bitmask)
        else:
            self.cell_editor.set_bitmask(0) # Empty cell

        # Update button states
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < len(self.current_braille_text) - 1)
        self.btn_delete.setEnabled(bool(self.current_braille_text))
        
        self.text_changed.emit(self.get_braille_text())


    def move_prev_char(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_ui()

    def move_next_char(self):
        if self.current_index < len(self.current_braille_text) - 1:
            self.current_index += 1
            self.update_ui()

    def insert_char(self):
        # Insert a blank braille character (bitmask 0) at the current index
        self.current_braille_text.insert(self.current_index, chr(0x2800))
        self.update_ui()

    def delete_char(self):
        if self.current_braille_text:
            del self.current_braille_text[self.current_index]
            if self.current_index >= len(self.current_braille_text) and self.current_index > 0:
                self.current_index -= 1
            self.update_ui()

    def update_current_braille_char(self, bitmask):
        if self.current_braille_text and 0 <= self.current_index < len(self.current_braille_text):
            self.current_braille_text[self.current_index] = chr(0x2800 + bitmask)
            self.update_ui()
        elif not self.current_braille_text:
            # If text is empty, insert the new char
            self.current_braille_text.append(chr(0x2800 + bitmask))
            self.update_ui()
                
    def get_braille_text(self):
        return "".join(self.current_braille_text)
