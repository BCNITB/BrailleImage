import numpy as np
from PySide6.QtWidgets import QVBoxLayout, QTextEdit, QPushButton, QMessageBox, QWidget
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import braille_processor
import sympy
from function_analyzer import analyze_composite_function
from ui.function_analysis_dialog import FunctionAnalysisDialog
from ui.graph_widget import GraphWidget
from error_handler import log_error

class CompositeMatplotlibWidget(QWidget):
    def __init__(self, function_domain_pairs, parent=None):
        super().__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.plot(function_domain_pairs)

    def plot(self, function_domain_pairs):
        ax = self.figure.add_subplot(111)
        ax.clear() # Clear previous plot

        overall_x_min = float('inf')
        overall_x_max = float('-inf')
        overall_y_min = float('inf')
        overall_y_max = float('-inf')

        plot_data = [] # Store x, y for each function

        for function_str, domain_info in function_domain_pairs:
            x_min = domain_info['lower_bound']
            x_max = domain_info['upper_bound']

            # Handle infinite bounds for initial range calculation
            if x_min == float('-inf'): x_min_plot = -10
            else: x_min_plot = x_min
            if x_max == float('inf'): x_max_plot = 10
            else: x_max_plot = x_max

            # Update overall x range
            overall_x_min = min(overall_x_min, x_min_plot)
            overall_x_max = max(overall_x_max, x_max_plot)

            x = np.linspace(x_min_plot, x_max_plot, 500)
            y = self._evaluate_function_safe(function_str, x)

            if y is None:
                QMessageBox.critical(self, self.tr("Function Error"), self.tr(f"Error plotting one of the functions: {function_str}"))
                self.canvas.draw()
                return

            plot_data.append((x, y, function_str, domain_info))

            # Update overall y range
            overall_y_min = min(overall_y_min, np.min(y))
            overall_y_max = max(overall_y_max, np.max(y))

        if not plot_data:
            ax.text(0.5, 0.5, self.tr("No functions to plot."), horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            self.canvas.draw()
            return

        # Plot all functions
        for x, y, function_str, domain_info in plot_data:
            ax.plot(x, y, label=f"y = {function_str} in {domain_info['left_bracket']}{domain_info['lower_bound']}, {domain_info['upper_bound']}{domain_info['right_bracket']}")
        
        ax.set_xlim(overall_x_min, overall_x_max)
        ax.set_ylim(overall_y_min, overall_y_max)

        ax.grid(True, which='both')
        ax.axhline(y=0, color='k')
        ax.axvline(x=0, color='k')
        ax.legend()
        ax.set_title(self.tr("Composite Function Graph"))
        self.canvas.draw()

    def _evaluate_function_safe(self, function_str, x_values):
        is_scalar = not isinstance(x_values, np.ndarray)
        if is_scalar:
            x_values = np.array([x_values])

        safe_dict = {'x': x_values, 'np': np, 'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                     'sqrt': np.sqrt, 'log': np.log, 'exp': np.exp, 'abs': np.abs,
                     'pi': np.pi, 'e': np.e}
        
        try:
            result = eval(function_str, {"__builtins__": None}, safe_dict)
            if isinstance(result, (int, float, complex)):
                result = np.full_like(x_values, result)

            return result.item() if is_scalar else result
        except Exception as e:
            log_error(f"Error evaluating function: {function_str}. Error: {e}")
            return None

class CompositeGraphWidget(GraphWidget):
    def __init__(self, function_domain_pairs, parent=None):
        super().__init__(title="Composite Function Graph", parent=parent)
        self.function_domain_pairs = function_domain_pairs
        
        # Override the graph_widget with the specialized one
        self.graph_widget = CompositeMatplotlibWidget(self.function_domain_pairs, self)
        self.main_layout.insertWidget(0, self.graph_widget) # Insert at top

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

    def analyze_function(self):
        analysis_result = analyze_composite_function(self.function_domain_pairs)
        analysis_text = analysis_result.get('summary_text', "Análisis no disponible.")
        braille_analysis = braille_processor.convert_text_to_braille(analysis_text, 'spanish', 6)
        
        dialog = FunctionAnalysisDialog(analysis_result, braille_analysis, self)
        dialog.exec()

    def generate_braille_graph(self):
        width = 40
        height = 20
        grid = [['⠀' for _ in range(width)] for _ in range(height)]

        overall_x_min = float('inf')
        overall_x_max = float('-inf')
        overall_y_min = float('inf')
        overall_y_max = float('-inf')

        all_y_values = []

        for function_str, domain_info in self.function_domain_pairs:
            x_min_math = domain_info['lower_bound']
            x_max_math = domain_info['upper_bound']

            x_min_plot = -10 if x_min_math == float('-inf') else x_min_math
            x_max_plot = 10 if x_max_math == float('inf') else x_max_math
            
            overall_x_min = min(overall_x_min, x_min_plot)
            overall_x_max = max(overall_x_max, x_max_plot)

            x_values_for_range = np.linspace(x_min_plot, x_max_plot, 100)
            y_values = self.graph_widget._evaluate_function_safe(function_str, x_values_for_range)
            
            if y_values is None:
                self.braille_display.setText(self.tr("Error al graficar la función."))
                return
            
            valid_indices = None
            left_bracket = domain_info['left_bracket']
            right_bracket = domain_info['right_bracket']
            
            if left_bracket == '(' and right_bracket == ')':
                valid_indices = np.where((x_values_for_range > x_min_math) & (x_values_for_range < x_max_math))
            elif left_bracket == '[' and right_bracket == ')':
                valid_indices = np.where((x_values_for_range >= x_min_math) & (x_values_for_range < x_max_math))
            elif left_bracket == '(' and right_bracket == ']':
                valid_indices = np.where((x_values_for_range > x_min_math) & (x_values_for_range <= x_max_math))
            elif left_bracket == '[' and right_bracket == ']':
                valid_indices = np.where((x_values_for_range >= x_min_math) & (x_values_for_range <= x_max_math))
            
            if valid_indices is not None and y_values[valid_indices].size > 0:
                all_y_values.extend(y_values[valid_indices])

        if not all_y_values:
            overall_y_min, overall_y_max = -5, 5
        else:
            overall_y_min = np.min(all_y_values)
            overall_y_max = np.max(all_y_values)

        if overall_y_min == overall_y_max:
            overall_y_min -= 5
            overall_y_max += 5

        # Draw Axes
        if overall_y_min <= 0 <= overall_y_max:
            y_axis_grid_pos = round((height - 1) * (overall_y_max - 0) / (overall_y_max - overall_y_min))
            if 0 <= y_axis_grid_pos < height:
                for i in range(width):
                    if grid[y_axis_grid_pos][i] == '⠀':
                        grid[y_axis_grid_pos][i] = '⠂'

        if overall_x_min <= 0 <= overall_x_max:
            x_axis_grid_pos = round((width - 1) * (0 - overall_x_min) / (overall_x_max - overall_x_min))
            if 0 <= x_axis_grid_pos < width:
                for i in range(height):
                    if grid[i][x_axis_grid_pos] == '⠀':
                        grid[i][x_axis_grid_pos] = '⠂'

        # Draw the function lines
        for x_grid in range(width):
            x_math = overall_x_min + (x_grid / (width - 1)) * (overall_x_max - overall_x_min)
            
            target_function_str = None
            for function_str, domain_info in self.function_domain_pairs:
                lower_bound = domain_info['lower_bound']
                upper_bound = domain_info['upper_bound']
                left_bracket = domain_info['left_bracket']
                right_bracket = domain_info['right_bracket']

                in_domain = False
                if left_bracket == '(' and right_bracket == ')':
                    if lower_bound < x_math < upper_bound: in_domain = True
                elif left_bracket == '[' and right_bracket == ')':
                    if lower_bound <= x_math < upper_bound: in_domain = True
                elif left_bracket == '(' and right_bracket == ']':
                    if lower_bound < x_math <= upper_bound: in_domain = True
                elif left_bracket == '[' and right_bracket == ']':
                    if lower_bound <= x_math <= upper_bound: in_domain = True
                
                if in_domain:
                    target_function_str = function_str
                    break

            if target_function_str:
                y_math = self.graph_widget._evaluate_function_safe(target_function_str, x_math)
                if y_math is None:
                    continue

                if overall_y_max - overall_y_min == 0:
                    y_grid = height // 2
                else:
                    y_grid = round((height - 1) * (overall_y_max - y_math) / (overall_y_max - overall_y_min))

                if 0 <= y_grid < height:
                    grid[y_grid][x_grid] = '⠿'

        braille_text = ""
        for row in grid:
            braille_text += "".join(row) + "\n"

        braille_info_parts = []
        for i, (function_str, domain_info) in enumerate(self.function_domain_pairs):
            formula_text = f"f{i+1}(x) = {function_str}"
            braille_formula = braille_processor.convert_text_to_braille(formula_text, 'spanish', 6)
            braille_info_parts.append(braille_formula)

            domain_text_plain = f"Domain: {domain_info['left_bracket']}{domain_info['lower_bound']}, {domain_info['upper_bound']}{domain_info['right_bracket']}"
            braille_domain = braille_processor.convert_text_to_braille(domain_text_plain, 'spanish', 6)
            braille_info_parts.append(braille_domain)
            braille_info_parts.append("")

        if braille_info_parts:
            braille_text += "\n" + "\n".join(braille_info_parts)

        self.braille_display.setText(braille_text)
