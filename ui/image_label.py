
from PySide6.QtWidgets import QLabel, QApplication
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QPen

class ImageLabel(QLabel):
    """
    Una subclase de QLabel que permite al usuario dibujar un rectángulo de selección
    y emite una señal con el rectángulo seleccionado.
    """
    # Señal que emite el rectángulo de selección (en coordenadas del widget)
    new_selection = Signal(QRect)
    selection_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True) # Necesario para recibir eventos de movimiento del ratón
        self.crop_active = False
        self.is_cropping = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.selection_rect = QRect()

    def set_crop_active(self, active):
        """Activa o desactiva el modo de recorte."""
        self.crop_active = active
        if self.crop_active:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            self.clear_selection()

    def clear_selection(self):
        """Limpia el rectángulo de selección actual."""
        self.selection_rect = QRect()
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_cropping = False
        self.update() # Vuelve a dibujar para eliminar el rectángulo
        self.selection_cleared.emit()

    def mousePressEvent(self, event):
        if self.crop_active and event.button() == Qt.LeftButton:
            self.start_point = event.position().toPoint()
            self.selection_rect = QRect(self.start_point, QPoint())
            self.is_cropping = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_cropping:
            self.end_point = event.position().toPoint()
            self.selection_rect = QRect(self.start_point, self.end_point).normalized()
            self.update() # Vuelve a dibujar para mostrar el rectángulo actualizado
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_cropping and event.button() == Qt.LeftButton:
            self.is_cropping = False
            self.new_selection.emit(self.selection_rect)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        """Dibuja el QLabel y, encima, el rectángulo de selección si existe."""
        super().paintEvent(event)
        if not self.selection_rect.isNull() and self.crop_active:
            painter = QPainter(self)
            pen = QPen(Qt.red, 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect)
