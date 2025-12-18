from PySide6.QtWidgets import QVBoxLayout, QTextEdit, QPushButton, QMessageBox
from PySide6.QtGui import QFont
import numpy as np
from ui.graph_widget import GraphWidget
import braille_processor
from function_analyzer import analyze_linear_function
from ui.function_analysis_dialog import FunctionAnalysisDialog
from error_handler import log_error

class LinearGraphWidget(GraphWidget):
    def __init__(self, slope, intercept, show_equation=True, show_roots=True, parent=None):
        super().__init__(title="Linear Function Graph", parent=parent)
        self.slope = slope
        self.intercept = intercept
        self.show_equation = show_equation
        self.show_roots = show_roots # Fix: ensure show_roots is assigned
        self.plot_linear_graph()
        self.generate_braille_graph() # Call after plotting

        # Analysis button
        self.analysis_button = QPushButton("Analizar la función")
        self.analysis_button.clicked.connect(self.analyze_function)
        self.main_layout.addWidget(self.analysis_button)

    def plot_linear_graph(self):
        x = np.linspace(-10, 10, 100)
        y = self.slope * x + self.intercept

        title_parts = []
        if self.show_equation:
            formula = f"y = {self.slope}x"
            if self.intercept > 0:
                formula += f" + {self.intercept}"
            elif self.intercept < 0:
                formula += f" - {abs(self.intercept)}"
            title_parts.append(formula)

        if self.show_roots:
            if self.slope != 0:
                x_intercept = -self.intercept / self.slope
                intercept_text = f"X-intercept: ({x_intercept:.2f}, 0)"
            else:
                intercept_text = "The line is horizontal, no X-intercept." if self.intercept != 0 else "The line is the X-axis."
            title_parts.append(intercept_text)

        self.plot_graph(x, y, "\n".join(title_parts), "X-axis", "Y-axis")

    def analyze_function(self):
        analysis_result = analyze_linear_function(self.slope, self.intercept)
        analysis_text = analysis_result.get('summary_text', "Análisis no disponible.")
        braille_analysis = braille_processor.convert_text_to_braille(analysis_text, 'spanish', 6)
        
        dialog = FunctionAnalysisDialog(analysis_result, braille_analysis, self)
        dialog.exec()

    def generate_braille_graph(self):
        width = 40
        height = 20
        grid = [['⠀' for _ in range(width)] for _ in range(height)]

        x_min_math = -10
        x_max_math = 10

        x_values_for_range = np.linspace(x_min_math, x_max_math, width)
        y_values = self.slope * x_values_for_range + self.intercept
        y_min_math = np.min(y_values)
        y_max_math = np.max(y_values)

        if y_min_math == y_max_math:
            y_min_math -= 5
            y_max_math += 5

        if y_min_math <= 0 <= y_max_math:
            y_axis_grid_pos = round((height - 1) * (y_max_math - 0) / (y_max_math - y_min_math))
            if 0 <= y_axis_grid_pos < height:
                for i in range(width):
                    if grid[y_axis_grid_pos][i] == '⠀':
                        grid[y_axis_grid_pos][i] = '⠂'

        if x_min_math <= 0 <= x_max_math:
            x_axis_grid_pos = round((width - 1) * (0 - x_min_math) / (x_max_math - x_min_math))
            if 0 <= x_axis_grid_pos < width:
                for i in range(height):
                    if grid[i][x_axis_grid_pos] == '⠀':
                        grid[i][x_axis_grid_pos] = '⠂'

        for x_grid in range(width):
            x_math = x_min_math + (x_grid / (width - 1)) * (x_max_math - x_min_math)
            y_math = self.slope * x_math + self.intercept

            if y_max_math - y_min_math == 0:
                y_grid = height // 2
            else:
                y_grid = round((height - 1) * (y_max_math - y_math) / (y_max_math - y_min_math))

            if 0 <= y_grid < height:
                grid[y_grid][x_grid] = '⠿'

        braille_text = ""
        for row in grid:
            braille_text += "".join(row) + "\n"

        braille_info_parts = []
        if self.show_equation:
            formula_text = f"y = {self.slope}x"
            if self.intercept > 0:
                formula_text += f" + {self.intercept}"
            elif self.intercept < 0:
                formula += f" - {abs(self.intercept)}"
            braille_formula = braille_processor.convert_text_to_braille(formula_text, 'spanish', 6)
            braille_info_parts.append(braille_formula)

        if self.show_roots:
            if self.slope != 0:
                x_intercept = -self.intercept / self.slope
                intercept_text_plain = f"X-intercept: ({x_intercept:.2f}, 0)"
            else:
                intercept_text_plain = "The line is horizontal, no X-intercept." if self.intercept != 0 else "The line is the X-axis."
            braille_intercept = braille_processor.convert_text_to_braille(intercept_text_plain, 'spanish', 6)
            braille_info_parts.append(braille_intercept)

        if braille_info_parts:
            braille_text += "\n" + "\n".join(braille_info_parts)

        self.braille_display.setText(braille_text)
