from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QFileDialog, QMessageBox, QLabel
from PySide6.QtCore import Qt
import json
import os
import logging

class CustomBrailleTableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Gestionar Tablas Braille Personalizadas"))
        self.setGeometry(200, 200, 600, 400)

        self.custom_tables = {}
        self.load_saved_custom_tables()

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        main_layout.addWidget(QLabel(self.tr("Tablas Braille Personalizadas Cargadas:")))
        self.table_list_widget = QListWidget()
        main_layout.addWidget(self.table_list_widget)

        button_layout = QHBoxLayout()
        self.load_button = QPushButton(self.tr("Cargar Tabla desde Archivo..."))
        self.load_button.clicked.connect(self.load_custom_table_from_file)
        button_layout.addWidget(self.load_button)

        self.remove_button = QPushButton(self.tr("Eliminar Tabla Seleccionada"))
        self.remove_button.clicked.connect(self.remove_selected_table)
        button_layout.addWidget(self.remove_button)

        self.close_button = QPushButton(self.tr("Cerrar"))
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)
        self.update_table_list()

    def _show_error_message(self, title, message, detailed_message=""):
        logging.error(f"{title}: {message}\n{detailed_message}")
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        if detailed_message:
            msg_box.setInformativeText(detailed_message)
        msg_box.exec()

    def load_saved_custom_tables(self):
        # This method will load custom tables from a persistent storage (e.g., QSettings or a dedicated file)
        # For now, we'll just initialize an empty dictionary.
        pass

    def update_table_list(self):
        self.table_list_widget.clear()
        for name in self.custom_tables.keys():
            self.table_list_widget.addItem(name)

    def load_custom_table_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Cargar Tabla Braille Personalizada"), "", self.tr("Archivos JSON (*.json)"))
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Validate the structure of the JSON file
                required_keys = ["name", "language_code", "dots_mode", "mapping"]
                if not all(k in data for k in required_keys):
                    self._show_error_message(self.tr("Error de Formato"),
                                             self.tr("El archivo JSON no tiene el formato esperado."),
                                             self.tr(f"Faltan claves requeridas: {', '.join(required_keys)}."))
                    return
                
                table_name = data["name"]
                if not isinstance(table_name, str) or not table_name.strip():
                    self._show_error_message(self.tr("Error de Formato"),
                                             self.tr("El nombre de la tabla no es válido."),
                                             self.tr("La clave 'name' debe ser una cadena no vacía."))
                    return

                if not isinstance(data["language_code"], str) or not data["language_code"].strip():
                    self._show_error_message(self.tr("Error de Formato"),
                                             self.tr("El código de idioma no es válido."),
                                             self.tr("La clave 'language_code' debe ser una cadena no vacía."))
                    return

                dots_mode = data["dots_mode"]
                if not isinstance(dots_mode, int) or dots_mode not in [6, 8]:
                    self._show_error_message(self.tr("Error de Formato"),
                                             self.tr("El modo de puntos Braille no es válido."),
                                             self.tr("La clave 'dots_mode' debe ser 6 u 8."))
                    return

                mapping = data["mapping"]
                if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
                    self._show_error_message(self.tr("Error de Formato"),
                                             self.tr("El mapa de caracteres no es válido."),
                                             self.tr("La clave 'mapping' debe ser un diccionario con claves y valores de cadena."))
                    return

                if table_name in self.custom_tables:
                    reply = QMessageBox.question(self, self.tr("Tabla Existente"),
                                                 self.tr(f"La tabla '{table_name}' ya existe. ¿Deseas sobrescribirla?"),
                                                 QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.No:
                        return

                # Generate reverse mapping if not provided
                if "reverse_mapping" not in data:
                    data["reverse_mapping"] = {v: k for k, v in data["mapping"].items()}

                self.custom_tables[table_name] = data
                self.update_table_list()
                QMessageBox.information(self, self.tr("Tabla Cargada"), self.tr(f"Tabla '{table_name}' cargada exitosamente."))

            except FileNotFoundError:
                self._show_error_message(self.tr("Archivo no Encontrado"),
                                         self.tr("El archivo especificado no existe."),
                                         self.tr(f"Ruta: {file_path}"))
            except json.JSONDecodeError as e:
                self._show_error_message(self.tr("Error de JSON"),
                                         self.tr("El archivo seleccionado no es un JSON válido."),
                                         self.tr(f"Detalles: {e}"))
            except Exception as e:
                self._show_error_message(self.tr("Error al Cargar"),
                                         self.tr(f"Ocurrió un error inesperado al cargar la tabla."),
                                         self.tr(f"Detalles: {e}"))

    def remove_selected_table(self):
        selected_items = self.table_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("Ninguna Selección"), self.tr("Por favor, selecciona una tabla para eliminar."))
            return

        table_name = selected_items[0].text()
        reply = QMessageBox.question(self, self.tr("Confirmar Eliminación"),
                                     self.tr(f"¿Estás seguro de que deseas eliminar la tabla '{table_name}'?"),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                del self.custom_tables[table_name]
                self.update_table_list()
                QMessageBox.information(self, self.tr("Tabla Eliminada"), self.tr(f"Tabla '{table_name}' eliminada exitosamente."))
            except KeyError:
                self._show_error_message(self.tr("Error de Eliminación"),
                                         self.tr(f"La tabla '{table_name}' no se encontró."),
                                         self.tr("Esto puede ocurrir si la tabla ya fue eliminada o el nombre es incorrecto."))
            except Exception as e:
                self._show_error_message(self.tr("Error de Eliminación"),
                                         self.tr(f"Ocurrió un error inesperado al eliminar la tabla '{table_name}'."),
                                         self.tr(f"Detalles: {e}"))

    def get_custom_tables(self):
        return self.custom_tables

    def retranslate_ui(self):
        self.setWindowTitle(self.tr("Gestionar Tablas Braille Personalizadas"))
        # findChild is not reliable for retranslation if there are multiple QLabels without object names
        # It's better to assign object names or store references to the widgets.
        # For now, we'll retranslate the main label directly if it's the only one.
        # If there are multiple, we'd need to iterate or use specific object names.
        # Assuming the first QLabel is the one we want to retranslate here.
        labels = self.findChildren(QLabel)
        if labels:
            labels[0].setText(self.tr("Tablas Braille Personalizadas Cargadas:"))

        self.load_button.setText(self.tr("Cargar Tabla desde Archivo..."))
        self.remove_button.setText(self.tr("Eliminar Tabla Seleccionada"))
        self.close_button.setText(self.tr("Cerrar"))
