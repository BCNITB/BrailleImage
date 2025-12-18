from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QInputDialog, QFormLayout

class PointsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Introducir Puntos")
        self.points = []
        self.point_inputs = []

        self.layout = QVBoxLayout(self)

        # Initial setup to ask for number of points
        self.num_points_layout = QHBoxLayout()
        self.num_points_label = QLabel("Número de puntos:")
        self.num_points_input = QLineEdit()
        self.num_points_button = QPushButton("Crear Campos")
        self.num_points_button.clicked.connect(self.create_point_fields)
        
        self.num_points_layout.addWidget(self.num_points_label)
        self.num_points_layout.addWidget(self.num_points_input)
        self.num_points_layout.addWidget(self.num_points_button)
        self.layout.addLayout(self.num_points_layout)

        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_points)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

    def create_point_fields(self):
        # Clear previous fields
        for i in reversed(range(self.form_layout.count())): 
            self.form_layout.itemAt(i).widget().setParent(None)
        self.point_inputs.clear()

        try:
            num_points = int(self.num_points_input.text())
            if num_points <= 0:
                QMessageBox.warning(self, "Entrada no válida", "Por favor, introduzca un número positivo de puntos.")
                return
        except ValueError:
            QMessageBox.warning(self, "Entrada no válida", "Por favor, introduzca un número entero válido.")
            return

        for i in range(num_points):
            x_input = QLineEdit()
            y_input = QLineEdit()
            self.point_inputs.append((x_input, y_input))
            self.form_layout.addRow(f"Punto {i+1} (x, y):", QHBoxLayout())
            self.form_layout.itemAt(i, QFormLayout.FieldRole).layout().addWidget(x_input)
            self.form_layout.itemAt(i, QFormLayout.FieldRole).layout().addWidget(y_input)

    def accept_points(self):
        self.points.clear()
        try:
            for x_input, y_input in self.point_inputs:
                if not x_input.text() or not y_input.text():
                    QMessageBox.warning(self, "Entrada no válida", "Por favor, introduzca todos los valores.")
                    return
                x = float(x_input.text())
                y = float(y_input.text())
                self.points.append((x, y))
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "Entrada no válida", "Por favor, introduzca coordenadas numéricas válidas para todos los puntos.")
            self.points.clear()

    def get_points(self):
        return self.points

class LinearFunctionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Función Lineal")

        self.layout = QVBoxLayout(self)

        # Slope input
        self.slope_layout = QHBoxLayout()
        self.slope_label = QLabel("Pendiente (m):")
        self.slope_input = QLineEdit()
        self.slope_layout.addWidget(self.slope_label)
        self.slope_layout.addWidget(self.slope_input)
        self.layout.addLayout(self.slope_layout)

        # Intercept input
        self.intercept_layout = QHBoxLayout()
        self.intercept_label = QLabel("Corte en el eje Y (b):")
        self.intercept_input = QLineEdit()
        self.intercept_layout.addWidget(self.intercept_label)
        self.intercept_layout.addWidget(self.intercept_input)
        self.layout.addLayout(self.intercept_layout)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

    def accept(self):
        if not self.slope_input.text() or not self.intercept_input.text():
            QMessageBox.warning(self, "Entrada no válida", "Por favor, introduzca todos los valores.")
            return
        super().accept()

    def get_values(self):
        return self.slope_input.text(), self.intercept_input.text()

class QuadraticFunctionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Función Cuadrática")

        self.layout = QVBoxLayout(self)

        # Coefficient 'a'
        self.a_layout = QHBoxLayout()
        self.a_label = QLabel("Coeficiente cuadrático (a):")
        self.a_input = QLineEdit()
        self.a_layout.addWidget(self.a_label)
        self.a_layout.addWidget(self.a_input)
        self.layout.addLayout(self.a_layout)

        # Coefficient 'b'
        self.b_layout = QHBoxLayout()
        self.b_label = QLabel("Coeficiente lineal (b):")
        self.b_input = QLineEdit()
        self.b_layout.addWidget(self.b_label)
        self.b_layout.addWidget(self.b_input)
        self.layout.addLayout(self.b_layout)

        # Coefficient 'c'
        self.c_layout = QHBoxLayout()
        self.c_label = QLabel("Término independiente (c):")
        self.c_input = QLineEdit()
        self.c_layout.addWidget(self.c_label)
        self.c_layout.addWidget(self.c_input)
        self.layout.addLayout(self.c_layout)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

    def accept(self):
        if not self.a_input.text() or not self.b_input.text() or not self.c_input.text():
            QMessageBox.warning(self, "Entrada no válida", "Por favor, introduzca todos los valores.")
            return
        super().accept()

    def get_values(self):
        return self.a_input.text(), self.b_input.text(), self.c_input.text()

class CubicFunctionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Función Cúbica")

        self.layout = QVBoxLayout(self)

        # Coefficient 'a'
        self.a_layout = QHBoxLayout()
        self.a_label = QLabel("Coeficiente cúbico (a):")
        self.a_input = QLineEdit()
        self.a_layout.addWidget(self.a_label)
        self.a_layout.addWidget(self.a_input)
        self.layout.addLayout(self.a_layout)

        # Coefficient 'b'
        self.b_layout = QHBoxLayout()
        self.b_label = QLabel("Coeficiente cuadrático (b):")
        self.b_input = QLineEdit()
        self.b_layout.addWidget(self.b_label)
        self.b_layout.addWidget(self.b_input)
        self.layout.addLayout(self.b_layout)

        # Coefficient 'c'
        self.c_layout = QHBoxLayout()
        self.c_label = QLabel("Coeficiente lineal (c):")
        self.c_input = QLineEdit()
        self.c_layout.addWidget(self.c_label)
        self.c_layout.addWidget(self.c_input)
        self.layout.addLayout(self.c_layout)

        # Coefficient 'd'
        self.d_layout = QHBoxLayout()
        self.d_label = QLabel("Término independiente (d):")
        self.d_input = QLineEdit()
        self.d_layout.addWidget(self.d_label)
        self.d_layout.addWidget(self.d_input)
        self.layout.addLayout(self.d_layout)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

    def accept(self):
        if not self.a_input.text() or not self.b_input.text() or not self.c_input.text() or not self.d_input.text():
            QMessageBox.warning(self, "Entrada no válida", "Por favor, introduzca todos los valores.")
            return
        super().accept()

    def get_values(self):
        return self.a_input.text(), self.b_input.text(), self.c_input.text(), self.d_input.text()

class PolynomialFunctionDialog(QDialog):
    def __init__(self, degree, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Función Polinómica de Grado {degree}")
        self.degree = degree
        self.layout = QVBoxLayout(self)
        self.input_fields = []

        for i in range(self.degree, -1, -1):
            layout = QHBoxLayout()
            if i == 0:
                label_text = "Término independiente:"
            elif i == 1:
                label_text = "Coeficiente lineal (x):"
            elif i == 2:
                label_text = "Coeficiente cuadrático (x²):"
            elif i == 3:
                label_text = f"Coeficiente cúbico (x³):"
            else:
                label_text = f"Coeficiente de x^{i}:"
            
            label = QLabel(label_text)
            line_edit = QLineEdit()
            layout.addWidget(label)
            layout.addWidget(line_edit)
            self.layout.addLayout(layout)
            self.input_fields.append(line_edit)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

    def accept(self):
        for field in self.input_fields:
            if not field.text():
                QMessageBox.warning(self, "Entrada no válida", "Por favor, introduzca todos los valores.")
                return
        super().accept()

    def get_values(self):
        coeffs = []
        for field in self.input_fields:
            coeffs.append(field.text())
        return coeffs
