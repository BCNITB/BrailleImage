
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QToolButton
from PySide6.QtCore import Signal

class DrawingToolbar(QWidget):
    """
    Una barra de herramientas con botones para seleccionar las herramientas de dibujo Braille.
    """
    tool_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.pencil_button = QToolButton()
        self.pencil_button.setText("Lápiz")
        self.pencil_button.setCheckable(True)
        self.pencil_button.setChecked(True)
        self.pencil_button.setToolTip("Añade puntos Braille")
        self.pencil_button.clicked.connect(lambda: self._on_tool_selected('pencil'))
        layout.addWidget(self.pencil_button)

        self.eraser_button = QToolButton()
        self.eraser_button.setText("Goma")
        self.eraser_button.setCheckable(True)
        self.eraser_button.setToolTip("Borra puntos Braille")
        self.eraser_button.clicked.connect(lambda: self._on_tool_selected('eraser'))
        layout.addWidget(self.eraser_button)

        self.setLayout(layout)

    def _on_tool_selected(self, tool_name):
        """Gestiona la exclusividad de los botones de herramientas."""
        if tool_name == 'pencil':
            self.eraser_button.setChecked(False)
        elif tool_name == 'eraser':
            self.pencil_button.setChecked(False)
        
        # Asegurarse de que siempre haya una herramienta seleccionada
        if not self.pencil_button.isChecked() and not self.eraser_button.isChecked():
            self.pencil_button.setChecked(True)
            self.tool_selected.emit('pencil')
        else:
            self.tool_selected.emit(tool_name)
