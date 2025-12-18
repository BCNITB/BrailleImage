from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QTabWidget, QWidget
from PySide6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import sympy as sp
import re

class FunctionAnalysisDialog(QDialog):
    def __init__(self, analysis_result, braille_analysis, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Análisis de Función"))
        self.setGeometry(100, 100, 500, 400)

        self.analysis_result = analysis_result
        self.braille_analysis = braille_analysis

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        tab_widget = QTabWidget()
        
        # Text Analysis Tab
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        self.analysis_output = QTextEdit()
        self.analysis_output.setReadOnly(True)
        self.analysis_output.setText(self.analysis_result.get('summary_text', self.tr("No hay análisis disponible.")))
        self.analysis_output.setFocusPolicy(Qt.StrongFocus)
        self.analysis_output.setFocus()
        text_layout.addWidget(self.analysis_output)
        
        # Braille Analysis Tab
        braille_tab = QWidget()
        braille_layout = QVBoxLayout(braille_tab)
        self.braille_output = QTextEdit()
        self.braille_output.setReadOnly(True)
        self.braille_output.setText(self.braille_analysis)
        braille_layout.addWidget(self.braille_output)

        # Graph Tab
        graph_tab = QWidget()
        graph_layout = QVBoxLayout(graph_tab)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        graph_layout.addWidget(self.canvas)
        self.plot_function()
        
        tab_widget.addTab(text_tab, self.tr("Análisis en Texto"))
        tab_widget.addTab(braille_tab, self.tr("Análisis en Braille"))
        tab_widget.addTab(graph_tab, self.tr("Gráfico"))
        
        layout.addWidget(tab_widget)

        close_button = QPushButton(self.tr("Cerrar"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def plot_function(self):
        ax = self.figure.add_subplot(111)
        ax.clear()
        ax.set_title(self.tr("Gráfico de la Función"))
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(True)
        
        function_type = self.analysis_result.get('function_type')
        equation_str = self.analysis_result.get('equation')
        x_sym = sp.Symbol('x')
        f_expr = None
        
        try:
            if function_type == 'linear':
                # Parse 'y = mx + b' to get m and b
                parts = equation_str.replace('y = ', '').split('x + ')
                if len(parts) == 2:
                    slope = sp.sympify(parts[0])
                    intercept = sp.sympify(parts[1])
                    f_expr = slope * x_sym + intercept
                elif len(parts) == 1 and 'x' in equation_str: # e.g., y = mx
                    slope = sp.sympify(parts[0].replace('x', ''))
                    intercept = 0
                    f_expr = slope * x_sym
                else: # e.g., y = b (constant)
                    f_expr = sp.sympify(equation_str.replace('y = ', ''))

            elif function_type == 'quadratic' or function_type == 'cubic' or function_type == 'polynomial':
                # For these, the 'equation' in analysis_result is already a sympy-parseable string
                f_expr = sp.sympify(equation_str.replace('y = ', ''))
            
            elif function_type == 'composite':
                # Plot each piece of the composite function
                for piece in self.analysis_result['pieces_analysis']:
                    piece_eq_str = piece['equation']
                    piece_domain_str = piece['domain_interval']
                    piece_f_expr = sp.sympify(piece_eq_str)

                    # Extract numerical bounds from the string representation of the interval
                    match = re.match(r'\[?(-?oo|\d+\.?\d*),\s*(-?oo|\d+\.?\d*)\]?', piece_domain_str)
                    if match:
                        lower_bound_str = match.group(1).replace('oo', 'np.inf')
                        upper_bound_str = match.group(2).replace('oo', 'np.inf')
                        
                        lower_bound = float(eval(lower_bound_str))
                        upper_bound = float(eval(upper_bound_str))
                        
                        # Generate x_vals only within the piece's domain
                        if lower_bound == -np.inf: lower_bound = -10 # Default for plotting
                        if upper_bound == np.inf: upper_bound = 10 # Default for plotting

                        x_vals_piece = np.linspace(lower_bound, upper_bound, 100)
                        y_vals_piece = np.array([piece_f_expr.subs(x_sym, val) for val in x_vals_piece], dtype=float)
                        ax.plot(x_vals_piece, y_vals_piece, label=f"Tramo {piece['piece_number']}")
                ax.legend()
                self.canvas.draw()
                return # Exit early for composite as plotting is handled internally
            
            if f_expr:
                x_vals = np.linspace(-10, 10, 400) # Default range
                y_vals = np.array([f_expr.subs(x_sym, val) for val in x_vals], dtype=float)
                ax.plot(x_vals, y_vals, label=equation_str)
                ax.legend()

        except Exception as e:
            ax.text(0.5, 0.5, self.tr(f"Error al graficar: {e}"), horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            
        self.canvas.draw()