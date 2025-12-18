from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox, QTextEdit
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from workers import BrailleConversionWorker
from error_handler import log_error

class MatplotlibWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
        self.axes = self.figure.add_subplot(111)

class GraphWidget(QWidget):
    def __init__(self, title="Graph", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.graph_widget = MatplotlibWidget(self)
        self.main_layout.addWidget(self.graph_widget)

        self.braille_display = QTextEdit()
        self.braille_display.setReadOnly(True)
        self.braille_display.setFont(QFont("Courier New", 10))
        self.main_layout.addWidget(self.braille_display)

    def plot_graph(self, x, y, title, xlabel, ylabel):
        self.graph_widget.axes.clear()
        self.graph_widget.axes.plot(x, y)
        self.graph_widget.axes.set_title(title)
        self.graph_widget.axes.set_xlabel(xlabel)
        self.graph_widget.axes.set_ylabel(ylabel)
        self.graph_widget.canvas.draw()
