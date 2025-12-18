
import logging
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLabel, QSlider, QWidget, QVBoxLayout, QGroupBox
)
from PySide6.QtCore import Qt, Signal

class FilterSettingsPanel(QWidget):
    """
    Un panel de widgets para configurar los parámetros de los filtros de imagen en tiempo real.
    """
    # Señal emitida cuando cualquier parámetro cambia.
    parameters_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        # Diccionario para mantener un registro de los widgets de cada filtro
        self.filter_widgets = {}

        self._create_canny_widgets()
        self._create_sobel_widgets()
        self._create_laplacian_widgets()
        self._create_median_widgets()
        self._create_gaussian_widgets()
        self._create_bilateral_widgets()

        # Ocultar todos los grupos de widgets inicialmente
        self.show_filter_group('none')

    def _create_slider(self, min_val, max_val, initial_val, step=1):
        """Crea un QSlider con una configuración común."""
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(initial_val)
        slider.setSingleStep(step)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(int((max_val - min_val) / 10))
        slider.valueChanged.connect(self.parameters_changed.emit)
        return slider

    def _create_canny_widgets(self):
        """Crea los widgets para el filtro Canny."""
        group_box = QGroupBox("Ajustes de Canny")
        layout = QFormLayout()
        
        self.canny_thresh1_slider = self._create_slider(0, 500, 100)
        self.canny_thresh1_label = QLabel("100")
        self.canny_thresh1_slider.valueChanged.connect(lambda val: self.canny_thresh1_label.setText(str(val)))
        layout.addRow("Umbral 1:", self.canny_thresh1_slider)
        layout.addRow("", self.canny_thresh1_label)

        self.canny_thresh2_slider = self._create_slider(0, 500, 200)
        self.canny_thresh2_label = QLabel("200")
        self.canny_thresh2_slider.valueChanged.connect(lambda val: self.canny_thresh2_label.setText(str(val)))
        layout.addRow("Umbral 2:", self.canny_thresh2_slider)
        layout.addRow("", self.canny_thresh2_label)

        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
        self.filter_widgets['canny'] = group_box

    def _create_sobel_widgets(self):
        """Crea los widgets para el filtro Sobel."""
        group_box = QGroupBox("Ajustes de Sobel")
        layout = QFormLayout()

        self.sobel_ksize_slider = self._create_slider(1, 31, 5, step=2)
        self.sobel_ksize_label = QLabel("5")
        self.sobel_ksize_slider.valueChanged.connect(lambda val: self.sobel_ksize_label.setText(str(val) if val % 2 != 0 else str(val+1)))
        layout.addRow("Tamaño del Kernel:", self.sobel_ksize_slider)
        layout.addRow("", self.sobel_ksize_label)
        
        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
        self.filter_widgets['sobel'] = group_box

    def _create_laplacian_widgets(self):
        """Crea los widgets para el filtro Laplacian."""
        group_box = QGroupBox("Ajustes de Laplacian")
        layout = QFormLayout()

        self.laplacian_ksize_slider = self._create_slider(1, 31, 3, step=2)
        self.laplacian_ksize_label = QLabel("3")
        self.laplacian_ksize_slider.valueChanged.connect(lambda val: self.laplacian_ksize_label.setText(str(val) if val % 2 != 0 else str(val+1)))
        layout.addRow("Tamaño del Kernel:", self.laplacian_ksize_slider)
        layout.addRow("", self.laplacian_ksize_label)
        
        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
        self.filter_widgets['laplacian'] = group_box

    def _create_median_widgets(self):
        """Crea los widgets para el filtro de Mediana."""
        group_box = QGroupBox("Ajustes de Filtro de Mediana")
        layout = QFormLayout()

        self.median_ksize_slider = self._create_slider(1, 31, 5, step=2)
        self.median_ksize_label = QLabel("5")
        self.median_ksize_slider.valueChanged.connect(lambda val: self.median_ksize_label.setText(str(val) if val % 2 != 0 else str(val+1)))
        layout.addRow("Tamaño del Kernel:", self.median_ksize_slider)
        layout.addRow("", self.median_ksize_label)
        
        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
        self.filter_widgets['median'] = group_box

    def _create_gaussian_widgets(self):
        """Crea los widgets para el filtro Gaussiano."""
        group_box = QGroupBox("Ajustes de Filtro Gaussiano")
        layout = QFormLayout()

        self.gaussian_ksize_slider = self._create_slider(1, 31, 5, step=2)
        self.gaussian_ksize_label = QLabel("5")
        self.gaussian_ksize_slider.valueChanged.connect(lambda val: self.gaussian_ksize_label.setText(str(val) if val % 2 != 0 else str(val+1)))
        layout.addRow("Tamaño del Kernel:", self.gaussian_ksize_slider)
        layout.addRow("", self.gaussian_ksize_label)
        
        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
        self.filter_widgets['gaussian'] = group_box

    def _create_bilateral_widgets(self):
        """Crea los widgets para el filtro Bilateral."""
        group_box = QGroupBox("Ajustes de Filtro Bilateral")
        layout = QFormLayout()

        self.bilateral_d_slider = self._create_slider(1, 15, 9)
        self.bilateral_d_label = QLabel("9")
        self.bilateral_d_slider.valueChanged.connect(lambda val: self.bilateral_d_label.setText(str(val)))
        layout.addRow("Diámetro (d):", self.bilateral_d_slider)
        layout.addRow("", self.bilateral_d_label)

        self.bilateral_sigma_color_slider = self._create_slider(1, 200, 75)
        self.bilateral_sigma_color_label = QLabel("75")
        self.bilateral_sigma_color_slider.valueChanged.connect(lambda val: self.bilateral_sigma_color_label.setText(str(val)))
        layout.addRow("Sigma Color:", self.bilateral_sigma_color_slider)
        layout.addRow("", self.bilateral_sigma_color_label)

        self.bilateral_sigma_space_slider = self._create_slider(1, 200, 75)
        self.bilateral_sigma_space_label = QLabel("75")
        self.bilateral_sigma_space_slider.valueChanged.connect(lambda val: self.bilateral_sigma_space_label.setText(str(val)))
        layout.addRow("Sigma Espacio:", self.bilateral_sigma_space_slider)
        layout.addRow("", self.bilateral_sigma_space_label)

        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
        self.filter_widgets['bilateral'] = group_box

    def show_filter_group(self, filter_name):
        """Muestra el grupo de widgets para el filtro especificado y oculta los demás."""
        logging.debug(f"Mostrando grupo de filtros para: {filter_name}")
        found = False
        for name, widget in self.filter_widgets.items():
            if name == filter_name:
                widget.setVisible(True)
                found = True
            else:
                widget.setVisible(False)
        
        # Si el filter_name no corresponde a ningún grupo, se ocultan todos.
        self.setVisible(found)

    def set_parameters(self, params):
        """Establece los valores de los sliders a partir de un diccionario."""
        # Bloquear señales para evitar actualizaciones mientras se establecen los valores
        self.blockSignals(True)
        try:
            self.canny_thresh1_slider.setValue(params.get('canny_threshold1', 100))
            self.canny_thresh2_slider.setValue(params.get('canny_threshold2', 200))
            self.sobel_ksize_slider.setValue(params.get('sobel_kernel_size', 5))
            self.laplacian_ksize_slider.setValue(params.get('laplacian_kernel_size', 3))
            self.median_ksize_slider.setValue(params.get('median_kernel_size', 5))
            self.gaussian_ksize_slider.setValue(params.get('gaussian_kernel_size', 5))
            self.bilateral_d_slider.setValue(params.get('bilateral_d', 9))
            self.bilateral_sigma_color_slider.setValue(params.get('bilateral_sigma_color', 75))
            self.bilateral_sigma_space_slider.setValue(params.get('bilateral_sigma_space', 75))
        finally:
            # Desbloquear señales en cualquier caso
            self.blockSignals(False)


    def get_parameters(self):
        """Devuelve un diccionario con los parámetros actuales de todos los filtros."""
        # Asegura que los valores impares para los kernels sean correctos
        sobel_ksize = self.sobel_ksize_slider.value()
        if sobel_ksize % 2 == 0: sobel_ksize += 1

        laplacian_ksize = self.laplacian_ksize_slider.value()
        if laplacian_ksize % 2 == 0: laplacian_ksize += 1

        median_ksize = self.median_ksize_slider.value()
        if median_ksize % 2 == 0: median_ksize += 1
        
        gaussian_ksize = self.gaussian_ksize_slider.value()
        if gaussian_ksize % 2 == 0: gaussian_ksize += 1

        return {
            'canny_threshold1': self.canny_thresh1_slider.value(),
            'canny_threshold2': self.canny_thresh2_slider.value(),
            'sobel_kernel_size': sobel_ksize,
            'laplacian_kernel_size': laplacian_ksize,
            'median_kernel_size': median_ksize,
            'gaussian_kernel_size': gaussian_ksize,
            'bilateral_d': self.bilateral_d_slider.value(),
            'bilateral_sigma_color': self.bilateral_sigma_color_slider.value(),
            'bilateral_sigma_space': self.bilateral_sigma_space_slider.value(),
        }
