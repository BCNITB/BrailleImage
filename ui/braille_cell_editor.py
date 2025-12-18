from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, Signal, QSize, QRect, QEvent

class BrailleCellEditor(QWidget):
    dot_pattern_changed = Signal(int) # Emits the new bitmask

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 150) # Fixed size for a single cell editor
        self.bitmask = 0 # Represents the 8 dots
        self.dot_radius = 10
        self.dot_spacing_x = 20
        self.dot_spacing_y = 20
        self.margin_x = 15
        self.margin_y = 15
        self.setAccessibleName("Editor de Celda Braille")
        self.update_accessible_description()
        self.setFocusPolicy(Qt.StrongFocus) # Enable keyboard focus
        self.focused_dot = 1 # Keep track of the currently focused dot

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the 8 dots
        dot_positions = {
            1: (self.margin_x, self.margin_y),
            2: (self.margin_x, self.margin_y + self.dot_spacing_y),
            3: (self.margin_x, self.margin_y + 2 * self.dot_spacing_y),
            7: (self.margin_x, self.margin_y + 3 * self.dot_spacing_y), # Dot 7

            4: (self.margin_x + self.dot_spacing_x, self.margin_y),
            5: (self.margin_x + self.dot_spacing_x, self.margin_y + self.dot_spacing_y),
            6: (self.margin_x + self.dot_spacing_x, self.margin_y + 2 * self.dot_spacing_y),
            8: (self.margin_x + self.dot_spacing_x, self.margin_y + 3 * self.dot_spacing_y), # Dot 8
        }

        for i, (x, y) in dot_positions.items():
            if (self.bitmask >> (i - 1)) & 1: # Check if dot is "on"
                painter.setBrush(QColor(0, 0, 0)) # Black dot
            else:
                painter.setBrush(QColor(200, 200, 200)) # Grey outline for "off" dot
            painter.drawEllipse(x, y, self.dot_radius * 2, self.dot_radius * 2)

            if i == self.focused_dot:
                painter.setPen(QColor(255, 0, 0)) # Red outline for focused dot
                painter.drawEllipse(x, y, self.dot_radius * 2, self.dot_radius * 2)
                painter.setPen(Qt.NoPen)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Determine which dot was clicked
            dot_positions = {
                1: (self.margin_x, self.margin_y),
                2: (self.margin_x, self.margin_y + self.dot_spacing_y),
                3: (self.margin_x, self.margin_y + 2 * self.dot_spacing_y),
                7: (self.margin_x, self.margin_y + 3 * self.dot_spacing_y),

                4: (self.margin_x + self.dot_spacing_x, self.margin_y),
                5: (self.margin_x + self.dot_spacing_x, self.margin_y + self.dot_spacing_y),
                6: (self.margin_x + self.dot_spacing_x, self.margin_y + 2 * self.dot_spacing_y),
                8: (self.margin_x + self.dot_spacing_x, self.margin_y + 3 * self.dot_spacing_y),
            }

            for i, (dx, dy) in dot_positions.items():
                dot_rect = QRect(dx, dy, self.dot_radius * 2, self.dot_radius * 2)
                if dot_rect.contains(event.pos()):
                    self.bitmask ^= (1 << (i - 1)) # Toggle the bit
                    self.update() # Redraw the widget
                    self.update_accessible_description()
                    self.dot_pattern_changed.emit(self.bitmask)
                    return

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            if self.focused_dot == 1: self.focused_dot = 3
            elif self.focused_dot == 2: self.focused_dot = 1
            elif self.focused_dot == 3: self.focused_dot = 2
            elif self.focused_dot == 4: self.focused_dot = 6
            elif self.focused_dot == 5: self.focused_dot = 4
            elif self.focused_dot == 6: self.focused_dot = 5
            elif self.focused_dot == 7: self.focused_dot = 2
            elif self.focused_dot == 8: self.focused_dot = 5
            self.update()
        elif event.key() == Qt.Key_Down:
            if self.focused_dot == 1: self.focused_dot = 2
            elif self.focused_dot == 2: self.focused_dot = 3
            elif self.focused_dot == 3: self.focused_dot = 7
            elif self.focused_dot == 4: self.focused_dot = 5
            elif self.focused_dot == 5: self.focused_dot = 6
            elif self.focused_dot == 6: self.focused_dot = 8
            elif self.focused_dot == 7: self.focused_dot = 1
            elif self.focused_dot == 8: self.focused_dot = 4
            self.update()
        elif event.key() == Qt.Key_Left:
            if self.focused_dot in [4, 5, 6, 8]:
                self.focused_dot -= 3
            self.update()
        elif event.key() == Qt.Key_Right:
            if self.focused_dot in [1, 2, 3, 7]:
                self.focused_dot += 3
            self.update()
        elif event.key() == Qt.Key_Space or event.key() == Qt.Key_Return:
            self.bitmask ^= (1 << (self.focused_dot - 1))
            self.update()
            self.update_accessible_description()
            self.dot_pattern_changed.emit(self.bitmask)
        else:
            super().keyPressEvent(event)

    def set_bitmask(self, bitmask):
        if self.bitmask != bitmask:
            self.bitmask = bitmask
            self.update()
            self.update_accessible_description()

    def get_bitmask(self):
        return self.bitmask

    def update_accessible_description(self):
        dots_on = [str(i) for i in DOT_POSITIONS.keys() if (self.bitmask >> (i - 1)) & 1]
        description = f"Celda Braille con puntos activados: {', '.join(dots_on) if dots_on else 'ninguno'}. Carácter Braille: {chr(0x2800 + self.bitmask)}"
        self.setAccessibleDescription(description)
        # Notify screen reader about the change
        QApplication.instance().postEvent(self, QEvent(QEvent.AccessibilityDescriptionChange))

    def sizeHint(self):
        return QSize(self.margin_x * 2 + self.dot_spacing_x + self.dot_radius * 2,
                     self.margin_y * 2 + 3 * self.dot_spacing_y + self.dot_radius * 2)
