from PySide6.QtWidgets import QVBoxLayout, QTextEdit, QPushButton, QMessageBox, QInputDialog
from PySide6.QtGui import QFont
import numpy as np
from ui.graph_widget import GraphWidget
import braille_processor
from error_handler import log_error

class PointsGraphWidget(GraphWidget):
    def __init__(self, points, parent=None):
        super().__init__(title="Points Graph", parent=parent)
        self.points = points
        self.fitted_function = None
        self.fitted_function_str = ""
        self.plot_points_graph()

        # Adjust function button
        self.adjust_button = QPushButton("Adjust Function")
        self.adjust_button.clicked.connect(self.adjust_function)
        self.main_layout.addWidget(self.adjust_button)

        # Braille graph display
        self.braille_display = QTextEdit()
        self.braille_display.setReadOnly(True)
        self.braille_display.setFont(QFont("Courier New", 10))
        self.main_layout.addWidget(self.braille_display)

        self.generate_braille_graph()

    def plot_points_graph(self, fitted_function=None):
        x_coords, y_coords = zip(*self.points)
        self.graph_widget.axes.clear()
        if self.points:
            self.graph_widget.axes.scatter(x_coords, y_coords, label="Points")
        
        if fitted_function is not None:
            x_fit = np.linspace(min(x_coords), max(x_coords), 100)
            y_fit = fitted_function(x_fit)
            self.graph_widget.axes.plot(x_fit, y_fit, 'r-', label=f"Fitted Function: {self.fitted_function_str}")

        self.graph_widget.axes.grid(True, which='both')
        self.graph_widget.axes.axhline(y=0, color='k')
        self.graph_widget.axes.axvline(x=0, color='k')
        self.graph_widget.axes.set_title("Points Graph and Fitted Function")
        self.graph_widget.axes.legend()
        self.graph_widget.canvas.draw()

    def adjust_function(self):
        degree, ok = QInputDialog.getInt(self, "Polynomial Degree", "Enter the degree of the polynomial for fitting:", 1, 1, 10, 1)
        if not ok:
            return

        x_coords, y_coords = zip(*self.points)
        coeffs = np.polyfit(x_coords, y_coords, degree)
        
        rounded_coeffs = [round(c, 2) for c in coeffs]
        self.fitted_function = np.poly1d(rounded_coeffs)
        
        self.fitted_function_str = "y = "
        for i, c in enumerate(rounded_coeffs):
            power = degree - i
            if abs(c) > 1e-6:
                if i > 0 and c > 0:
                    self.fitted_function_str += " + "
                elif i > 0 and c < 0:
                    self.fitted_function_str += " - "
                elif i == 0 and c < 0:
                    self.fitted_function_str += "-"

                self.fitted_function_str += f"{abs(c):.2f}"
                if power > 0:
                    self.fitted_function_str += f"x^{power}" if power > 1 else "x"

        self.plot_points_graph(self.fitted_function)
        self.generate_braille_graph()

    def generate_braille_graph(self):
        width = 40
        height = 20
        grid = [['⠀' for _ in range(width)] for _ in range(height)]

        if not self.points:
            self.braille_display.setText("No points to graph.")
            return

        x_coords, y_coords = zip(*self.points)
        x_min_math, x_max_math = min(x_coords), max(x_coords)
        y_min_math, y_max_math = min(y_coords), max(y_coords)

        if x_min_math == x_max_math:
            x_min_math -= 5
            x_max_math += 5
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

        # Draw Points
        for x_math, y_math in self.points:
            if x_max_math - x_min_math == 0:
                x_grid = width // 2
            else:
                x_grid = round((width - 1) * (x_math - x_min_math) / (x_max_math - x_min_math))

            if y_max_math - y_min_math == 0:
                y_grid = height // 2
            else:
                y_grid = round((height - 1) * (y_max_math - y_math) / (y_max_math - y_min_math))

            if 0 <= x_grid < width and 0 <= y_grid < height:
                grid[y_grid][x_grid] = '⠿'

        # Draw Fitted Function
        if self.fitted_function is not None:
            for x_grid in range(width):
                x_math = x_min_math + (x_grid / (width - 1)) * (x_max_math - x_min_math)
                y_math = self.fitted_function(x_math)
                
                if y_max_math - y_min_math == 0:
                    y_grid = height // 2
                else:
                    y_grid = round((height - 1) * (y_max_math - y_math) / (y_max_math - y_min_math))

                if 0 <= y_grid < height and grid[y_grid][x_grid] == '⠀':
                    grid[y_grid][x_grid] = '⠶'

        braille_text = ""
        for row in grid:
            braille_text += "".join(row) + "\n"

        points_text = "Points: " + ", ".join([f"({p[0]}, {p[1]})" for p in self.points])
        braille_points = braille_processor.convert_text_to_braille(points_text, 'spanish', 6)
        braille_text += "\n" + braille_points

        if self.fitted_function is not None:
            function_text = f"Fitted Function: {self.fitted_function_str}"
            braille_function = braille_processor.convert_text_to_braille(function_text, 'spanish', 6)
            braille_text += "\n" + braille_function

        self.braille_display.setText(braille_text)
