from PySide6.QtWidgets import QVBoxLayout, QTextEdit, QPushButton, QMessageBox
from PySide6.QtGui import QFont
import numpy as np
from ui.graph_widget import GraphWidget
import braille_processor
from function_analyzer import analyze_cubic_function
from ui.function_analysis_dialog import FunctionAnalysisDialog
from error_handler import log_error

class CubicGraphWidget(GraphWidget):
    def __init__(self, a, b, c, d, show_equation=True, show_roots=True, parent=None):
        super().__init__(title="Cubic Function Graph", parent=parent)
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.show_equation = show_equation
        self.show_roots = show_roots
        self.plot_cubic_graph()
        self.generate_braille_graph()

        # Analysis button
        self.analysis_button = QPushButton("Analizar la función")
        self.analysis_button.clicked.connect(self.analyze_function)
        self.main_layout.addWidget(self.analysis_button)

    def plot_cubic_graph(self):
        x = np.linspace(-10, 10, 100)
        y = self.a * x**3 + self.b * x**2 + self.c * x + self.d

        title_parts = []
        if self.show_equation:
            formula = f"y = {self.a}x³"
            if self.b > 0:
                formula += f" + {self.b}x²"
            elif self.b < 0:
                formula += f" - {abs(self.b)}x²"
            if self.c > 0:
                formula += f" + {self.c}x"
            elif self.c < 0:
                formula += f" - {abs(self.c)}x"
            if self.d > 0:
                formula += f" + {self.d}"
            elif self.d < 0:
                formula += f" - {abs(self.d)}"
            title_parts.append(formula)

        if self.show_roots:
            coeffs = [self.a, self.b, self.c, self.d]
            roots = np.roots(coeffs)
            real_roots = roots[np.isreal(roots)].real
            
            if len(real_roots) > 0:
                intercept_text = "Roots (X-intercepts): " + ", ".join([f"({root:.2f}, 0)" for root in sorted(real_roots)])
            else:
                intercept_text = "No real roots (does not intersect X-axis)."
            title_parts.append(intercept_text)

        self.plot_graph(x, y, "\n".join(title_parts), "X-axis", "Y-axis")

    def analyze_function(self):
        analysis_result = analyze_cubic_function(self.a, self.b, self.c, self.d)
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
        y_values = self.a * x_values_for_range**3 + self.b * x_values_for_range**2 + self.c * x_values_for_range + self.d
        y_min_math = np.min(y_values)
        y_max_math = np.max(y_values)

        if y_min_math == y_max_math:
            y_min_math -= 5
            y_max_math += 5

        # Draw Axes
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

        # Draw Line
        for x_grid in range(width):
            x_math = x_min_math + (x_grid / (width - 1)) * (x_max_math - x_min_math)
            y_math = self.a * x_math**3 + self.b * x_math**2 + self.c * x_math + self.d

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
            formula_text = f"y = {self.a}x³"
            if self.b > 0:
                formula_text += f" + {self.b}x²"
            elif self.b < 0:
                formula_text += f" - {abs(self.b)}x²"
            if self.c > 0:
                formula_text += f" + {self.c}x"
            elif self.c < 0:
                formula_text += f" - {abs(self.c)}x"
            if self.d > 0:
                formula_text += f" + {self.d}"
            elif self.d < 0:
                formula_text += f" - {abs(self.d)}"
            braille_formula = braille_processor.convert_text_to_braille(formula_text, 'spanish', 6)
            braille_info_parts.append(braille_formula)

        if self.show_roots:
            coeffs = [self.a, self.b, self.c, self.d]
            roots = np.roots(coeffs)
            real_roots = roots[np.isreal(roots)].real

            if len(real_roots) > 0:
                intercept_text_plain = "Roots (X-intercepts): " + ", ".join([f"({root:.2f}, 0)" for root in sorted(real_roots)])
            else:
                intercept_text_plain = "No real roots (does not intersect X-axis)."
            braille_intercept = braille_processor.convert_text_to_braille(intercept_text_plain, 'spanish', 6)
            braille_info_parts.append(braille_intercept)

        if braille_info_parts:
            braille_text += "\n" + "\n".join(braille_info_parts)

        self.braille_display.setText(braille_text)