import re
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox, QGridLayout, QWidget, QScrollArea
from PySide6.QtCore import Qt, Signal

class IntervalInputWidget(QWidget):
    remove_requested = Signal(QWidget)

    def __init__(self, interval_index, parent=None):
        super().__init__(parent)
        self.interval_index = interval_index
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.function_label = QLabel(self.tr(f"Función {interval_index + 1} (ej. x**2):"))
        self.function_input = QLineEdit()
        self.function_input.setPlaceholderText(self.tr("Introduce la función para este intervalo"))

        self.domain_label = QLabel(self.tr(f"Dominio {interval_index + 1} de X:"))
        
        self.lower_bound_type = QComboBox()
        self.lower_bound_type.addItems([self.tr("Abierto"), self.tr("Cerrado")])
        self.lower_bound_input = QLineEdit()
        self.lower_bound_input.setPlaceholderText(self.tr("Límite inferior (ej. -inf, 0)"))

        self.upper_bound_input = QLineEdit()
        self.upper_bound_input.setPlaceholderText(self.tr("Límite superior (ej. 5, inf)"))
        self.upper_bound_type = QComboBox()
        self.upper_bound_type.addItems([self.tr("Abierto"), self.tr("Cerrado")])

        self.remove_button = QPushButton(self.tr("Eliminar Intervalo"))
        self.remove_button.clicked.connect(self._on_remove_clicked)

        self.layout.addWidget(self.function_label, 0, 0, 1, 4)
        self.layout.addWidget(self.function_input, 1, 0, 1, 4)
        self.layout.addWidget(self.domain_label, 2, 0, 1, 4)
        
        self.layout.addWidget(self.lower_bound_type, 3, 0)
        self.layout.addWidget(self.lower_bound_input, 3, 1)
        self.layout.addWidget(QLabel(","), 3, 2)
        self.layout.addWidget(self.upper_bound_input, 3, 3)
        self.layout.addWidget(self.upper_bound_type, 3, 4)
        self.layout.addWidget(self.remove_button, 4, 0, 1, 5)

    def _on_remove_clicked(self):
        self.remove_requested.emit(self)

    def get_interval_data(self):
        function_str = self.function_input.text()
        lower_bound_str = self.lower_bound_input.text()
        upper_bound_str = self.upper_bound_input.text()

        if not function_str:
            raise ValueError(self.tr(f"Por favor, introduce la función para el intervalo {self.interval_index + 1}."))
        if not lower_bound_str or not upper_bound_str:
            raise ValueError(self.tr(f"Por favor, introduce los límites del dominio para el intervalo {self.interval_index + 1}."))
        
        lower_bound = float('-inf') if lower_bound_str == '-inf' else float(lower_bound_str)
        upper_bound = float('inf') if upper_bound_str == 'inf' else float(upper_bound_str)

        if lower_bound >= upper_bound:
            raise ValueError(self.tr(f"El límite inferior debe ser menor que el límite superior para el intervalo {self.interval_index + 1}."))

        domain_info = {
            'left_bracket': '(' if self.lower_bound_type.currentText() == self.tr("Abierto") else '[',
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'right_bracket': ')' if self.upper_bound_type.currentText() == self.tr("Abierto") else ']'
        }
        return function_str, domain_info

class CompositeFunctionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Función Compuesta"))
        self.setModal(True)
        self.all_parsed_data = None

        self.main_layout = QVBoxLayout(self)
        
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.intervals_container = QWidget()
        self.intervals_layout = QVBoxLayout(self.intervals_container)
        self.intervals_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.intervals_container)
        self.main_layout.addWidget(self.scroll_area)

        self.interval_widgets = []
        self._add_interval_widget() # Start with one interval

        self.add_interval_button = QPushButton(self.tr("Añadir Intervalo"))
        self.add_interval_button.clicked.connect(self._add_interval_widget)
        self.main_layout.addWidget(self.add_interval_button)

        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton(self.tr("Aceptar"))
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton(self.tr("Cancelar"))
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.button_layout)

    def _add_interval_widget(self):
        new_index = len(self.interval_widgets)
        interval_widget = IntervalInputWidget(new_index, self)
        interval_widget.remove_requested.connect(self._remove_interval_widget)
        self.intervals_layout.addWidget(interval_widget)
        self.interval_widgets.append(interval_widget)
        self._update_remove_buttons_visibility()
        self.scroll_area.ensureWidgetVisible(interval_widget)
        interval_widget.function_input.setFocus()

    def _remove_interval_widget(self, widget_to_remove):
        if len(self.interval_widgets) > 1: # Ensure at least one interval remains
            self.intervals_layout.removeWidget(widget_to_remove)
            self.interval_widgets.remove(widget_to_remove)
            widget_to_remove.deleteLater()
            # Re-index remaining widgets
            for i, widget in enumerate(self.interval_widgets):
                widget.interval_index = i
                widget.function_label.setText(self.tr(f"Función {i + 1} (ej. x**2):"))
                widget.domain_label.setText(self.tr(f"Dominio {i + 1} de X:"))
            self._update_remove_buttons_visibility()
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Debe haber al menos un intervalo."))

    def _update_remove_buttons_visibility(self):
        # Only show remove button if there's more than one interval
        for widget in self.interval_widgets:
            widget.remove_button.setVisible(len(self.interval_widgets) > 1)

    def accept(self):
        self.all_parsed_data = []
        for interval_widget in self.interval_widgets:
            try:
                function_str, domain_info = interval_widget.get_interval_data()
                self.all_parsed_data.append((function_str, domain_info))
            except ValueError as e:
                QMessageBox.warning(self, self.tr("Dominio Inválido"), str(e))
                self.all_parsed_data = [] # Clear any partially collected data
                return
        super().accept()

    def get_parsed_data(self):
        return self.all_parsed_data
