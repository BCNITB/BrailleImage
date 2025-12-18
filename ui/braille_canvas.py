
import numpy as np
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

import braille_processor

class BrailleCanvas(QWidget):
    """
    Un widget que actúa como un lienzo para dibujar y editar gráficos táctiles
    directamente como puntos Braille.
    """
    content_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(palette)

        self.dot_matrix = np.array([[]])
        self.dot_size = 4  # Radio del punto
        self.grid_spacing = self.dot_size * 3 # Espacio entre puntos de la rejilla
        
        self.active_tool = 'pencil'
        self.is_drawing = False

    def set_braille_string(self, braille_string):
        """Convierte un string Braille a una matriz de puntos y la carga en el lienzo."""
        if not braille_string:
            self.dot_matrix = np.full((30, 40 * 2), False)
            return

        lines = braille_string.split('\n')
        num_rows = len(lines) * 4 # 4 filas de puntos por línea de texto (para 8 puntos)
        num_cols = max(len(line) for line in lines) * 2 if lines else 0

        self.dot_matrix = np.full((num_rows, num_cols), False)

        for r, line in enumerate(lines):
            for c, char in enumerate(line):
                dot_pattern = braille_processor.get_dot_pattern(char)
                if not dot_pattern: continue

                cell_row_start = r * 4
                cell_col_start = c * 2

                for i in range(8):
                    if (dot_pattern >> i) & 1:
                        row = cell_row_start + (i % 4)
                        col = cell_col_start + (i // 4)
                        if row < self.dot_matrix.shape[0] and col < self.dot_matrix.shape[1]:
                            self.dot_matrix[row, col] = True
        self.update_canvas_size()
        self.update()
        self.content_changed.emit()

    def get_braille_string(self):
        """Convierte la matriz de puntos de nuevo a un string Braille."""
        if self.dot_matrix.size == 0:
            return ""
        
        num_rows, num_cols = self.dot_matrix.shape
        braille_lines = []
        
        for r in range(0, num_rows, 4):
            line_str = ""
            for c in range(0, num_cols, 2):
                dot_pattern = 0
                for i in range(8):
                    row = r + (i % 4)
                    col = c + (i // 4)
                    if row < num_rows and col < num_cols and self.dot_matrix[row, col]:
                        dot_pattern |= (1 << i)
                
                char = braille_processor.get_char_from_dot_pattern(dot_pattern)
                line_str += char
            braille_lines.append(line_str.rstrip())
        
        return '\n'.join(braille_lines)

    def update_canvas_size(self):
        """Ajusta el tamaño del widget para que quepa toda la matriz de puntos."""
        if self.dot_matrix.size == 0:
            return
        h, w = self.dot_matrix.shape
        new_width = w * self.grid_spacing + self.grid_spacing
        new_height = h * self.grid_spacing + self.grid_spacing
        self.setFixedSize(new_width, new_height)

    def paintEvent(self, event):
        """Dibuja la rejilla de puntos Braille."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.dot_matrix.size == 0:
            return

        dot_color = QColor(Qt.black)
        grid_color = QColor(220, 220, 220) # Gris claro

        num_rows, num_cols = self.dot_matrix.shape

        # Dibuja la rejilla de fondo
        pen = QPen(grid_color, 0.5, Qt.SolidLine)
        painter.setPen(pen)
        for r in range(num_rows + 1):
            y = r * self.grid_spacing + (self.grid_spacing / 2)
            painter.drawLine(0, y, num_cols * self.grid_spacing, y)
        for c in range(num_cols + 1):
            x = c * self.grid_spacing + (self.grid_spacing / 2)
            painter.drawLine(x, 0, x, num_rows * self.grid_spacing)

        # Dibuja los puntos
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(dot_color))
        for r in range(num_rows):
            for c in range(num_cols):
                if self.dot_matrix[r, c]:
                    center_x = c * self.grid_spacing + (self.grid_spacing / 2)
                    center_y = r * self.grid_spacing + (self.grid_spacing / 2)
                    painter.drawEllipse(QPoint(center_x, center_y), self.dot_size, self.dot_size)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drawing = True
            self._apply_tool(event.position().toPoint())

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self._apply_tool(event.position().toPoint())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drawing = False
            self.content_changed.emit()

    def set_tool(self, tool):
        self.active_tool = tool

    def _apply_tool(self, pos):
        """Aplica la herramienta activa en la posición del ratón."""
        col = int(pos.x() / self.grid_spacing)
        row = int(pos.y() / self.grid_spacing)

        if 0 <= row < self.dot_matrix.shape[0] and 0 <= col < self.dot_matrix.shape[1]:
            if self.active_tool == 'pencil':
                if not self.dot_matrix[row, col]:
                    self.dot_matrix[row, col] = True
                    self.update()
            elif self.active_tool == 'eraser':
                if self.dot_matrix[row, col]:
                    self.dot_matrix[row, col] = False
                    self.update()
