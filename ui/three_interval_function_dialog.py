from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QGridLayout
from PySide6.QtCore import Qt

class ThreeIntervalFunctionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Función Compuesta - Tres Intervalos"))
        self.setModal(True)
        self.parsed_data = None

        self.layout = QVBoxLayout(self)
        grid_layout = QGridLayout()

        # Split point 'a'
        self.split_point_a_label = QLabel(self.tr("Límite inferior del dominio (a):"))
        self.split_point_a_input = QLineEdit()
        self.split_point_a_input.setPlaceholderText(self.tr("Introduce el valor de 'a'"))
        
        # Split point 'b'
        self.split_point_b_label = QLabel(self.tr("Límite superior del dominio (b):"))
        self.split_point_b_input = QLineEdit()
        self.split_point_b_input.setPlaceholderText(self.tr("Introduce el valor de 'b'"))

        # Function for x = a
        self.function_equal_a_label = QLabel()
        self.function_equal_a_input = QLineEdit()
        self.function_equal_a_input.setPlaceholderText(self.tr("Función para x = a"))

        # Function for a < x < b
        self.function_between_ab_label = QLabel()
        self.function_between_ab_input = QLineEdit()
        self.function_between_ab_input.setPlaceholderText(self.tr("Función para a < x < b"))

        # Function for x = b
        self.function_equal_b_label = QLabel()
        self.function_equal_b_input = QLineEdit()
        self.function_equal_b_input.setPlaceholderText(self.tr("Función para x = b"))

        # Connect split point inputs to update labels
        self.split_point_a_input.textChanged.connect(self.update_labels)
        self.split_point_b_input.textChanged.connect(self.update_labels)

        grid_layout.addWidget(self.split_point_a_label, 0, 0)
        grid_layout.addWidget(self.split_point_a_input, 0, 1)
        grid_layout.addWidget(self.split_point_b_label, 1, 0)
        grid_layout.addWidget(self.split_point_b_input, 1, 1)
        
        grid_layout.addWidget(self.function_equal_a_label, 2, 0)
        grid_layout.addWidget(self.function_equal_a_input, 2, 1)
        grid_layout.addWidget(self.function_between_ab_label, 3, 0)
        grid_layout.addWidget(self.function_between_ab_input, 3, 1)
        grid_layout.addWidget(self.function_equal_b_label, 4, 0)
        grid_layout.addWidget(self.function_equal_b_input, 4, 1)

        self.layout.addLayout(grid_layout)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton(self.tr("Aceptar"))
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton(self.tr("Cancelar"))
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

        self.update_labels() # Initial label text

    def update_labels(self):
        split_value_a = self.split_point_a_input.text()
        split_value_b = self.split_point_b_input.text()

        if not split_value_a:
            split_value_a = "a"
        if not split_value_b:
            split_value_b = "b"

        self.function_equal_a_label.setText(self.tr(f"f(x) si x = {split_value_a}:"))
        self.function_between_ab_label.setText(self.tr(f"f(x) si {split_value_a} < x < {split_value_b}:"))
        self.function_equal_b_label.setText(self.tr(f"f(x) si x = {split_value_b}:"))

    def accept(self):
        func_equal_a_str = self.function_equal_a_input.text()
        func_between_ab_str = self.function_between_ab_input.text()
        func_equal_b_str = self.function_equal_b_input.text()
        
        split_point_a_str = self.split_point_a_input.text()
        split_point_b_str = self.split_point_b_input.text()

        if not all([func_equal_a_str, func_between_ab_str, func_equal_b_str, split_point_a_str, split_point_b_str]):
            QMessageBox.warning(self, self.tr("Entrada Inválida"), self.tr("Por favor, rellena todos los campos."))
            return
        
        try:
            split_point_a = float(split_point_a_str)
            split_point_b = float(split_point_b_str)

            if split_point_a >= split_point_b:
                QMessageBox.warning(self, self.tr("Entrada Inválida"), self.tr("El límite inferior 'a' debe ser menor que el límite superior 'b'."))
                return

            self.parsed_data = [
                (func_equal_a_str, {
                    'left_bracket': '[', 
                    'lower_bound': split_point_a, 
                    'upper_bound': split_point_a, 
                    'right_bracket': ']'
                }),
                (func_between_ab_str, {
                    'left_bracket': '(', 
                    'lower_bound': split_point_a, 
                    'upper_bound': split_point_b, 
                    'right_bracket': ')'
                }),
                (func_equal_b_str, {
                    'left_bracket': '[', 
                    'lower_bound': split_point_b, 
                    'upper_bound': split_point_b, 
                    'right_bracket': ']'
                })
            ]
            super().accept()
        except ValueError:
            QMessageBox.warning(self, self.tr("Entrada Inválida"), self.tr("Los límites del dominio 'a' y 'b' deben ser números."))
            return

    def get_parsed_data(self):
        return self.parsed_data
