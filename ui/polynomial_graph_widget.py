from PySide6.QtWidgets import QVBoxLayout, QTextEdit, QPushButton, QMessageBox
from PySide6.QtGui import QFont
import numpy as np
from ui.graph_widget import GraphWidget
import braille_processor
from function_analyzer import analyze_polynomial_function
from ui.function_analysis_dialog import FunctionAnalysisDialog
from error_handler import log_error

class PolynomialGraphWidget(GraphWidget):
    def __init__(self, coeffs, show_equation=True, show_roots=True, parent=None):
        super().__init__(title="Polynomial Function Graph", parent=parent)
        self.coeffs = coeffs
        self.show_equation = show_equation
        self.show_roots = show_roots
        self.plot_polynomial_graph()

        # Braille graph display
        self.braille_display = QTextEdit()
        self.braille_display.setReadOnly(True)
        self.braille_display.setFont(QFont("Courier New", 10))
        self.main_layout.addWidget(self.braille_display)

        # Analysis button
        self.analysis_button = QPushButton("Function Analysis")
        self.analysis_button.clicked.connect(self.analyze_function)
        self.main_layout.addWidget(self.analysis_button)

        self.generate_braille_graph()

    def plot_polynomial_graph(self):
        x = np.linspace(-10, 10, 100)
        y = np.polyval(self.coeffs, x)

        title_parts = []
        if self.show_equation:
            formula = "y = "
            degree = len(self.coeffs) - 1
            for i, c in enumerate(self.coeffs):
                power = degree - i
                if c == 0:
                    continue

                # Sign and value
                if i == 0:
                    if c < 0:
                        formula += f"- {abs(c)}"
                    else:
                        formula += f"{c}"
                else:
                    if c < 0:
                        formula += f" - {abs(c)}"
                    else:
                        formula += f" + {c}"

                # Variable
                if power > 0:
                    formula += "x"
                if power > 1:
                    superscripts = {"2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"}
                    power_str = str(power)
                    for digit, sup in superscripts.items():
                        power_str = power_str.replace(digit, sup)
                    formula += power_str
                formula += " "
            title_parts.append(formula)

        if self.show_roots:
            roots = np.roots(self.coeffs)
            real_roots = roots[np.isreal(roots)].real
            
            if len(real_roots) > 0:
                intercept_text = "Roots (X-intercepts): " + ", ".join([f"({root:.2f}, 0)" for root in sorted(real_roots)])
            else:
                intercept_text = "No real roots (does not intersect X-axis)."
            title_parts.append(intercept_text)

        self.plot_graph(x, y, "\n".join(title_parts), "X-axis", "Y-axis")

    def analyze_function(self):
        analysis_result = analyze_polynomial_function(self.coeffs)
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
        y_values = np.polyval(self.coeffs, x_values_for_range)
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
            y_math = np.polyval(self.coeffs, x_math)

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
            formula_text = "y = "
            degree = len(self.coeffs) - 1
            for i, c in enumerate(self.coeffs):
                power = degree - i
                if c == 0:
                    continue

                if i == 0:
                    if c < 0:
                        formula_text += f"- {abs(c)}"
                    else:
                        formula_text += f"{c}"
                else:
                    if c < 0:
                        formula_text += f" - {abs(c)}"
                    else:
                        formula_text += f" + {c}"

                if power > 0:
                    formula_text += "x"
                if power > 1:
                    superscripts = {"2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"}
                    power_str = str(power)
                    for digit, sup in superscripts.items():
                        power_str = power_str.replace(digit, sup)
                    formula_text += power_str
                formula_text += " "
            braille_formula = braille_processor.convert_text_to_braille(formula_text, 'spanish', 6)
            braille_info_parts.append(braille_formula)

        if self.show_roots:
            roots = np.roots(self.coeffs)
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
