from PySide6.QtWidgets import QDialog, QVBoxLayout
from ui.points_graph_widget import PointsGraphWidget

class PointsGraphDisplayDialog(QDialog):
    def __init__(self, points, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Points Graph Display")
        
        self.main_layout = QVBoxLayout(self)
        self.ink_graph_widget = PointsGraphWidget(points, self)
        self.main_layout.addWidget(self.ink_graph_widget)
        
    def adjust_function(self):
        self.ink_graph_widget.adjust_function()
        
    @property
    def fitted_function(self):
        return self.ink_graph_widget.fitted_function
        
    @property
    def fitted_function_str(self):
        return self.ink_graph_widget.fitted_function_str

    def generate_braille_graph(self):
        self.ink_graph_widget.generate_braille_graph()
