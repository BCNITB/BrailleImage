import sys
import logging
import cv2
import numpy as np
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog,
    QMessageBox, QScrollArea, QSlider, QStatusBar, QInputDialog, QProgressDialog, QDialog, QStackedWidget, QTabWidget
)
from PySide6.QtGui import QPixmap, QFont, QImage, QAction, QKeySequence, QPainter, QFontMetrics, QActionGroup
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt, QTranslator, QLocale, QSettings, QCoreApplication, QTimer, QThreadPool, QByteArray, QBuffer, QIODevice
import json
import shiboken6
import image_processor
import braille_processor
import file_io
from workers import BatchWorker, Worker
from ui.braille_cell_editor import BrailleCellEditor
from ui.braille_text_editor import BrailleTextEditor
from ui.braille_printer_dialog import BraillePrinterDialog
from ui.braille_learning_dialog import BrailleLearningDialog
from ui.custom_braille_table_dialog import CustomBrailleTableDialog
from ui.filter_settings_panel import FilterSettingsPanel
from ui.image_label import ImageLabel
from ui.braille_canvas import BrailleCanvas
from ui.drawing_toolbar import DrawingToolbar
from error_handler import gui_error_handler
from ui.math_dialogs import LinearFunctionDialog, QuadraticFunctionDialog, CubicFunctionDialog, PolynomialFunctionDialog, PointsDialog
from ui.composite_function_dialog import CompositeFunctionDialog
from ui.three_interval_function_dialog import ThreeIntervalFunctionDialog
from ui.linear_graph_widget import LinearGraphWidget
from ui.quadratic_graph_widget import QuadraticGraphWidget
from ui.cubic_graph_widget import CubicGraphWidget
from ui.polynomial_graph_widget import PolynomialGraphWidget
from ui.points_graph_widget import PointsGraphWidget
from ui.composite_graph_widget import CompositeGraphWidget
from ui.function_analysis_dialog import FunctionAnalysisDialog
import function_analyzer
import win32print
import base64
from io import BytesIO
from gemini_client import GeminiClient
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Conversor a Braille"))
        self.setGeometry(100, 100, 800, 800)
        self.threadpool = QThreadPool()
        self.original_cv_img = None
        self.original_color_cv_img = None
        self.zoom_factor = 1.0
        self.supported_image_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".svg"]
        self.raw_braille_text = ""
        self.plain_text_content = ""
        self.image_path = None
        self.braille_dot_size = 5 # Default dot size for visualization
        self.braille_dot_spacing = 2 # Default spacing between dots for visualization
        self.braille_bg_color = (0, 0, 0) # Default background color (black)
        self.braille_dot_color = (255, 255, 255) # White dots
        self.current_language = 'spanish' # Default language
        self.custom_braille_tables = {} # To store loaded custom braille tables
        self.undo_stack = []
        self.redo_stack = []
        self.setAcceptDrops(True)
        self.setStatusBar(QStatusBar(self))
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.braille_dots_mode = 6  # Default to 6 dots
        self.show_equation = True # Default to showing equation
        self.show_roots = True # Default to showing roots
        self.translator = QTranslator()
        self.recent_file_actions = []
        self.max_recent_files = 10
        self.default_app_font = QApplication.instance().font() # Store initial application font
        self.current_color_mode = 'original' # Default color mode for display
        self.active_color_filters = [] # List of active color filters (e.g., 'red', 'green', 'blue')
        self.current_noise_reduction_filter = 'none' # Default noise reduction filter
        self.current_edge_detection_algorithm = 'none' # Default edge detection algorithm
        self.current_segmentation_algorithm = 'none'
        self.segmentation_rect = None
        self.crop_roi = None # (x, y, w, h) en coordenadas de la imagen original
        self.open_graph_dialogs = []
        self.graph_tabs = None # Initialize graph_tabs attribute
        self.current_function_data = None

        # DEPRECATED: Filter parameters are now managed by FilterSettingsPanel
        # self.median_kernel_size = 5
        # self.gaussian_kernel_size = 5
        # self.bilateral_d = 9
        # self.bilateral_sigma_color = 75
        # self.bilateral_sigma_space = 75
        # self.canny_threshold1 = 100
        # self.canny_threshold2 = 200
        # self.sobel_kernel_size = 5
        # self.laplacian_kernel_size = 3

        self.create_menu_bar()
        self.create_ui_widgets()
        self.retranslate_ui() # Initial UI translation

        self.enable_initial_actions(True)
        self.update_recent_files_menu()

        self._save_state() # Save initial state

        # Load saved language or detect system language
        settings = QSettings("BrailleApp", "BrailleConverter")
        last_lang = settings.value("language", QLocale.system().name()[:2])
        QTimer.singleShot(0, lambda: self.set_language(last_lang))

        # Load saved theme or detect system theme
        last_theme = settings.value("theme", 'system') # Default to system theme
        self.set_theme(last_theme)

        # Load saved font size or detect system font size
        last_font_size = settings.value("font_size", 'system') # Default to system font size
        self.set_font_size(last_font_size)

        # Load saved dots mode
        last_dots_mode = int(settings.value("braille_dots_mode", 6)) # Default to 6 dots
        self.set_braille_dots_mode(last_dots_mode)

        # Load saved image adjustment settings
        self.slider_brightness.setValue(int(settings.value("brightness", 0)))
        self.slider_contrast.setValue(int(settings.value("contrast", 100)))
        self.action_invert.setChecked(settings.value("invert", "false").lower() == "true")
        self.action_dithering.setChecked(settings.value("dithering", "false").lower() == "true")
        self.action_lines.setChecked(settings.value("lines", "false").lower() == "true")
        self.action_adaptive_thresholding.setChecked(settings.value("adaptive_thresholding", "false").lower() == "true")
        self.action_remove_noise.setChecked(settings.value("remove_noise", "false").lower() == "true")

        # Load saved math display settings
        self.show_equation = settings.value("show_equation", True, type=bool)
        self.action_show_equation.setChecked(self.show_equation)
        self.show_roots = settings.value("show_roots", True, type=bool)
        self.action_show_roots.setChecked(self.show_roots)

        # Load saved color mode
        last_color_mode = settings.value("color_mode", 'original') # Default to original
        self.set_color_mode(last_color_mode)

        # Load saved active color filters
        self.active_color_filters = settings.value("active_color_filters", [])
        self.action_color_red.setChecked('red' in self.active_color_filters)
        self.action_color_green.setChecked('green' in self.active_color_filters)
        self.action_color_blue.setChecked('blue' in self.active_color_filters)

        # Load saved noise reduction filter parameters
        self.median_kernel_size = int(settings.value("median_kernel_size", 5))
        self.gaussian_kernel_size = int(settings.value("gaussian_kernel_size", 5))
        self.bilateral_d = int(settings.value("bilateral_d", 9))
        self.bilateral_sigma_color = int(settings.value("bilateral_sigma_color", 75))
        self.bilateral_sigma_space = int(settings.value("bilateral_sigma_space", 75))

        # Load saved edge detection algorithm parameters
        self.canny_threshold1 = int(settings.value("canny_threshold1", 100))
        self.canny_threshold2 = int(settings.value("canny_threshold2", 200))
        self.sobel_kernel_size = int(settings.value("sobel_kernel_size", 5))
        self.laplacian_kernel_size = int(settings.value("laplacian_kernel_size", 3))

        # Load saved segmentation settings
        self.current_segmentation_algorithm = settings.value("segmentation_algorithm", 'none')
        segmentation_rect_str = settings.value("segmentation_rect", None)
        if segmentation_rect_str:
            self.segmentation_rect = tuple(map(int, segmentation_rect_str.split(',')))
        else:
            self.segmentation_rect = None

        # Load saved noise reduction filter
        last_noise_filter = settings.value("noise_reduction_filter", 'none') # Default to none
        self.set_noise_reduction_filter(last_noise_filter)

        # Load saved edge detection algorithm
        last_edge_algorithm = settings.value("edge_detection_algorithm", 'none') # Default to none
        self.set_edge_detection_algorithm(last_edge_algorithm)

    def retranslate_ui(self):
        self.setWindowTitle(self.tr("Conversor a Braille"))

        # Update main menu titles
        self.file_menu.setTitle(self.tr("&Archivo"))
        self.edit_menu.setTitle(self.tr("&Edición"))
        self.image_menu.setTitle(self.tr("&Imagen"))
        self.color_menu.setTitle(self.tr("&Color"))
        self.noise_reduction_menu.setTitle(self.tr("&Reducción de Ruido"))
        self.algorithm_menu.setTitle(self.tr("&Algoritmo"))
        self.braille_menu.setTitle(self.tr("&Braille"))
        self.settings_menu.setTitle(self.tr("&Configuración"))
        self.help_menu.setTitle(self.tr("&Ayuda"))
        self.math_menu.setTitle(self.tr("&Matemáticas"))

        # Update submenu titles
        self.load_braille_menu.setTitle(self.tr("Cargar B&raille..."))
        self.export_menu.setTitle(self.tr("E&xportar a..."))
        self.language_menu.setTitle(self.tr("&Idioma"))
        self.theme_menu.setTitle(self.tr("&Tema"))
        self.function_menu.setTitle(self.tr("&Función"))

        # Retranslate individual actions
        self.action_open_image.setText(self.tr("&Cargar Imagen..."))
        self.action_open_text.setText(self.tr("Cargar &Texto..."))
        self.action_open_gdoc.setText(self.tr("Cargar Google &Doc..."))
        self.action_batch_process.setText(self.tr("Procesar &Carpeta de Imágenes..."))
        self.action_open_bra.setText(self.tr("Formato &.bra"))
        self.action_open_brf_braille.setText(self.tr("Formato B&RF (.brf)"))
        self.action_save.setText(self.tr("&Guardar (.txt)..."))
        self.action_export_brf.setText(self.tr("Formato BR&F (.brf)"))
        self.action_export_bra.setText(self.tr("Formato B&RA (.bra)"))
        self.action_close.setText(self.tr("&Cerrar"))
        self.action_exit.setText(self.tr("&Salir"))
        self.action_print_braille.setText(self.tr("Imprimir en Impresora Braille..."))
        self.action_undo.setText(self.tr("&Deshacer"))
        self.action_redo.setText(self.tr("&Rehacer"))
        self.action_copy.setText(self.tr("&Copiar Braille al Portapapeles"))
        self.action_adjust.setText(self.tr("&Brillo y Contraste"))
        self.action_invert.setText(self.tr("&Invertir Colores"))
        self.action_dithering.setText(self.tr("&Difuminado (Dithering)"))
        self.action_lines.setText(self.tr("&Líneas"))
        self.action_adaptive_thresholding.setText(self.tr("&Umbral Adaptativo"))
        self.action_edge_none.setText(self.tr("&Ninguno"))
        self.action_edge_canny.setText(self.tr("&Canny"))
        self.action_edge_sobel.setText(self.tr("&Sobel"))
        self.action_edge_prewitt.setText(self.tr("&Prewitt"))
        self.action_edge_laplacian.setText(self.tr("&Laplacian"))
        self.action_remove_noise.setText(self.tr("&Quitar Ruido"))
        self.action_noise_none.setText(self.tr("&Ninguno"))
        self.action_noise_median.setText(self.tr("&Filtro Mediana"))
        self.action_noise_gaussian.setText(self.tr("&Filtro Gaussiano"))
        self.action_noise_bilateral.setText(self.tr("&Filtro Bilateral"))
        self.action_color_original.setText(self.tr("&Original Color"))
        self.action_color_grayscale.setText(self.tr("&Grayscale"))
        self.action_color_red.setText(self.tr("&Rojo"))
        self.action_color_green.setText(self.tr("&Verde"))
        self.action_color_blue.setText(self.tr("&Azul"))
        self.action_save_img_settings.setText(self.tr("Guardar Ajustes de Imagen..."))
        self.action_load_img_settings.setText(self.tr("Cargar Ajustes de Imagen..."))
        self.action_convert_to_braille.setText(self.tr("Convertir a Braille"))
        self.action_zoom_in_image.setText(self.tr("Aumentar Zoom Imagen"))
        self.action_zoom_out_image.setText(self.tr("Reducir Zoom Imagen"))
        self.action_describe_image.setText(self.tr("Describir Imagen con Gemini"))
        self.action_compare_images.setText(self.tr("Comparar Imágenes"))
        self.action_desbraille.setText(self.tr("&Desbraillar"))
        self.action_no_split_words.setText(self.tr("No &partir palabras"))
        self.action_visualize_braille.setText(self.tr("&Visualizar Braille"))
        self.action_braille_cell_editor.setText(self.tr("&Editor de Celdas Braille"))
        self.action_interactive_learning.setText(self.tr("&Modo de Aprendizaje Interactivo"))
        self.action_zoom_in_braille.setText(self.tr("Aumentar Zoom Braille"))
        self.action_zoom_out_braille.setText(self.tr("Reducir Zoom Braille"))
        self.action_6_dots.setText(self.tr("&6 puntos"))
        self.action_8_dots.setText(self.tr("&8 puntos"))
        self.action_lang_es.setText(self.tr("&Castellano"))
        self.action_lang_ca.setText(self.tr("&Català"))
        self.action_lang_eu.setText(self.tr("&Euskara"))
        self.action_lang_gl.setText(self.tr("&Galego"))
        self.action_lang_en.setText(self.tr("&English"))
        self.action_theme_system.setText(self.tr("&Sistema"))
        self.action_theme_dark.setText(self.tr("&Oscuro"))
        self.action_theme_light.setText(self.tr("&Claro"))
        self.action_theme_high_contrast.setText(self.tr("&Alto Contraste"))
        self.action_font_size_system.setText(self.tr("&Sistema"))
        self.action_font_size_14.setText(self.tr("&14 puntos"))
        self.action_font_size_16.setText(self.tr("&16 puntos"))
        self.action_font_size_18.setText(self.tr("&18 puntos"))
        self.action_font_size_22.setText(self.tr("&22 puntos"))
        self.action_font_size_32.setText(self.tr("&32 puntos"))
        self.action_show_shortcuts.setText(self.tr("&Atajos de Teclado..."))

        self.action_linear_function.setText(self.tr("&Lineal"))
        self.action_quadratic_function.setText(self.tr("&Cuadrática"))
        self.action_cubic_function.setText(self.tr("&Cúbica"))
        self.action_polynomial_function.setText(self.tr("&Polinómica"))
        self.action_show_equation.setText(self.tr("&Mostrar Ecuación"))
        self.action_show_roots.setText(self.tr("&Mostrar Raíces"))
        self.action_points_graph.setText(self.tr("Graficar &Puntos"))

        # Retranslate custom language actions
        for action in self.custom_language_actions:
            action.setText(self.tr(action.text()))

        # Retranslate individual action tooltips
        self.action_open_image.setToolTip(self.tr("Carga un archivo de imagen para convertirlo a Braille."))
        self.action_open_text.setToolTip(self.tr("Carga un archivo de texto (.txt, .docx, .pdf) para convertirlo a Braille."))
        self.action_open_gdoc.setToolTip(self.tr("Carga texto desde un documento de Google Docs."))
        self.action_open_url.setToolTip(self.tr("Carga texto desde una página web."))
        self.action_batch_process.setToolTip(self.tr("Convierte todas las imágenes de una carpeta a Braille."))
        self.action_open_bra.setToolTip(self.tr("Carga un archivo en formato Braille Unicode (.bra)."))
        self.action_open_brf_braille.setToolTip(self.tr("Carga un archivo en formato BRF para impresoras Braille."))
        self.action_save.setToolTip(self.tr("Guarda el resultado Braille o el texto desbraillado en un archivo .txt."))
        self.action_export_brf.setToolTip(self.tr("Exporta el resultado Braille a un archivo compatible con impresoras Braille (.brf)."))
        self.action_export_bra.setToolTip(self.tr("Exporta el resultado Braille a un archivo de texto Braille Unicode (.bra)."))
        self.action_close.setToolTip(self.tr("Cierra el archivo actual y limpia la interfaz."))
        self.action_exit.setToolTip(self.tr("Cierra la aplicación."))
        self.action_undo.setToolTip(self.tr("Deshace la última acción."))
        self.action_redo.setToolTip(self.tr("Rehace la última acción deshecha."))
        self.action_copy.setToolTip(self.tr("Copia el contenido del panel de resultados al portapapeles."))
        self.action_adjust.setToolTip(self.tr("Muestra u oculta los controles de brillo y contraste."))
        self.action_invert.setToolTip(self.tr("Invierte los colores de la imagen (blanco a negro y viceversa)."))
        self.action_dithering.setToolTip(self.tr("Aplica un algoritmo de difuminado para simular sombras."))
        self.action_lines.setToolTip(self.tr("Activa el modo de detección de líneas en lugar de puntos."))
        self.action_adaptive_thresholding.setToolTip(self.tr("Usa un umbral adaptativo en lugar de un umbral fijo."))
        self.action_edge_none.setToolTip(self.tr("No aplica ningún algoritmo de detección de bordes."))
        self.action_edge_canny.setToolTip(self.tr("Aplica el algoritmo Canny para detectar bordes."))
        self.action_edge_sobel.setToolTip(self.tr("Aplica el operador Sobel para detectar bordes."))
        self.action_edge_prewitt.setToolTip(self.tr("Aplica el operador Prewitt para detectar bordes."))
        self.action_edge_laplacian.setToolTip(self.tr("Aplica el operador Laplaciano para detectar bordes."))
        self.action_remove_noise.setToolTip(self.tr("Aplica un filtro para eliminar el ruido de la imagen."))
        self.action_noise_none.setToolTip(self.tr("No aplica ningún filtro de reducción de ruido."))
        self.action_noise_median.setToolTip(self.tr("Aplica un filtro de mediana para reducir el ruido."))
        self.action_noise_gaussian.setToolTip(self.tr("Aplica un filtro gaussiano para suavizar la imagen y reducir el ruido."))
        self.action_noise_bilateral.setToolTip(self.tr("Aplica un filtro bilateral para reducir el ruido mientras se preservan los bordes."))
        self.action_color_original.setToolTip(self.tr("Muestra la imagen en su color original."))
        self.action_color_grayscale.setToolTip(self.tr("Convierte la imagen a escala de grises."))
        self.action_color_red.setToolTip(self.tr("Filtra la imagen para mostrar solo el canal rojo."))
        self.action_color_green.setToolTip(self.tr("Filtra la imagen para mostrar solo el canal verde."))
        self.action_color_blue.setToolTip(self.tr("Filtra la imagen para mostrar solo el canal azul."))
        self.action_save_img_settings.setToolTip(self.tr("Guarda los ajustes actuales de brillo, contraste, etc. en un archivo."))
        self.action_load_img_settings.setToolTip(self.tr("Carga ajustes de brillo, contraste, etc. desde un archivo."))
        self.action_convert_to_braille.setToolTip(self.tr("Convierte la imagen actual a texto Braille."))
        self.action_zoom_in_image.setToolTip(self.tr("Aumenta el zoom de la imagen."))
        self.action_zoom_out_image.setToolTip(self.tr("Reduce el zoom de la imagen."))
        self.action_print_braille.setToolTip(self.tr("Envía el texto Braille a una impresora Braille conectada."))
        self.action_desbraille.setToolTip(self.tr("Convierte el texto Braille de vuelta a texto plano (tinta)."))
        self.action_no_split_words.setToolTip(self.tr("Evita que las palabras se dividan al final de una línea en la salida Braille."))
        self.action_visualize_braille.setToolTip(self.tr("Convierte el texto Braille en una imagen visual de los puntos."))
        self.action_braille_cell_editor.setToolTip(self.tr("Abre un editor para crear o modificar caracteres Braille de forma interactiva."))
        self.action_interactive_learning.setToolTip(self.tr("Abre un modo interactivo para aprender Braille."))
        self.action_zoom_in_braille.setToolTip(self.tr("Aumenta el tamaño de la fuente del texto Braille."))
        self.action_zoom_out_braille.setToolTip(self.tr("Reduce el tamaño de la fuente del texto Braille."))

        # Retranslate BrailleTextEditor specific strings
        # These are defined within BrailleTextEditor, but we need to ensure they are translated if the language changes
        # The BrailleTextEditor itself will call self.tr() for its own strings.
        # We only need to retranslate the action that opens it.

        # Retranslate other UI elements that are not menu actions
        self.lbl_image_preview.setText(self.tr("Arrastra una imagen aquí o cárgala desde el menú Archivo"))
        self.slider_brightness.setToolTip(self.tr("Ajusta el brillo"))
        self.slider_brightness.setAccessibleName(self.tr("Deslizador de brillo"))
        self.slider_brightness.setAccessibleDescription(self.tr("Aumenta o disminuye el brillo de la imagen."))
        self.lbl_contrast_value.setText("{:.2f}".format(self.slider_contrast.value() / 100.0))
        self.slider_contrast.setToolTip(self.tr("Ajusta el contraste"))
        self.slider_contrast.setAccessibleName(self.tr("Deslizador de contraste"))
        self.slider_contrast.setAccessibleDescription(self.tr("Aumenta o disminuye el contraste de la imagen."))
        self.braille_display.setPlaceholderText(self.tr("El resultado en Braille aparecerá aquí..."))
        self.braille_display.setAccessibleName(self.tr("Salida de texto Braille"))
        self.latin_display.setPlaceholderText(self.tr("El texto en tinta aparecerá aquí..."))
        self.latin_display.setAccessibleName(self.tr("Salida de texto plano (tinta)"))

        self.slider_dot_size.setToolTip(self.tr("Ajusta el tamaño de los puntos Braille"))
        self.slider_dot_size.setAccessibleName(self.tr("Deslizador de tamaño de punto Braille"))
        self.lbl_dot_size_value.setText(str(self.braille_dot_size))
        self.slider_dot_spacing.setToolTip(self.tr("Ajusta el espaciado entre puntos Braille"))
        self.slider_dot_spacing.setAccessibleName(self.tr("Deslizador de espaciado de punto Braille"))
        self.lbl_dot_spacing_value.setText(str(self.braille_dot_spacing))
        self.btn_default_colors.setText(self.tr("Colores por Defecto"))
        self.btn_default_colors.setAccessibleName(self.tr("Esquema de colores por defecto"))
        self.btn_inverted_colors.setAccessibleName(self.tr("Esquema de colores invertidos"))

        # Retranslate BraillePrinterDialog specific strings
        # These are defined within BraillePrinterDialog, but we need to ensure they are translated if the language changes
        # The BraillePrinterDialog itself will call self.tr() for its own strings.
        # We only need to retranslate the action that opens it.
        self.action_print_braille.setToolTip(self.tr("Envía el texto Braille a una impresora Braille conectada."))

        # Retranslate the placeholder texts for connection details
        # This is handled by update_connection_details_placeholder in BraillePrinterDialog
        # but we need to trigger it if the dialog is open.
        # For now, we assume the dialog is closed and reopened for language changes.


    def create_menu_bar(self):
        menu_bar = self.menuBar()
        self.file_menu = menu_bar.addMenu(self.tr("&Archivo"))
        self.action_open_image = QAction(self.tr("&Cargar Imagen..."), self); self.action_open_image.setShortcut("Ctrl+O"); self.action_open_image.setToolTip(self.tr("Carga un archivo de imagen para convertirlo a Braille.")); self.action_open_image.triggered.connect(self.open_image_dialog)
        self.file_menu.addAction(self.action_open_image)
        self.action_open_text = QAction(self.tr("Cargar &Texto..."), self); self.action_open_text.setShortcut("Ctrl+T"); self.action_open_text.setToolTip(self.tr("Carga un archivo de texto (.txt, .docx, .pdf) para convertirlo a Braille.")); self.action_open_text.triggered.connect(self.open_text_dialog)
        self.file_menu.addAction(self.action_open_text)
        self.action_open_gdoc = QAction(self.tr("Cargar Google &Doc..."), self); self.action_open_gdoc.setToolTip(self.tr("Carga texto desde un documento de Google Docs.")); self.action_open_gdoc.triggered.connect(self.open_google_doc_dialog)
        self.file_menu.addAction(self.action_open_gdoc)
        self.action_open_url = QAction(self.tr("Cargar desde &URL..."), self)
        self.action_open_url.setToolTip(self.tr("Carga texto desde una página web."))
        self.action_open_url.triggered.connect(self.open_url_dialog)
        self.file_menu.addAction(self.action_open_url)
        self.action_batch_process = QAction(self.tr("Procesar &Carpeta de Imágenes..."), self); self.action_batch_process.setShortcut("Ctrl+Shift+O"); self.action_batch_process.setToolTip(self.tr("Convierte todas las imágenes de una carpeta a Braille.")); self.action_batch_process.triggered.connect(self.start_batch_process)
        self.file_menu.addAction(self.action_batch_process)
        self.file_menu.addSeparator()
        self.load_braille_menu = self.file_menu.addMenu(self.tr("Cargar B&raille..."))
        self.action_open_bra = QAction(self.tr("Formato &.bra"), self); self.action_open_bra.setToolTip(self.tr("Carga un archivo en formato Braille Unicode (.bra).")); self.action_open_bra.triggered.connect(self.open_bra_dialog)
        self.load_braille_menu.addAction(self.action_open_bra)
        self.action_open_brf_braille = QAction(self.tr("Formato B&RF (.brf)"), self); self.action_open_brf_braille.setToolTip(self.tr("Carga un archivo en formato BRF para impresoras Braille.")); self.action_open_brf_braille.triggered.connect(self.open_brf_dialog)
        self.load_braille_menu.addAction(self.action_open_brf_braille)
        self.action_save = QAction(self.tr("&Guardar (.txt)..."), self); self.action_save.setShortcut("Ctrl+S"); self.action_save.setToolTip(self.tr("Guarda el resultado Braille o el texto desbraillado en un archivo .txt.")); self.action_save.triggered.connect(self.save_result_dialog)
        self.file_menu.addAction(self.action_save)
        self.export_menu = self.file_menu.addMenu(self.tr("E&xportar a..."))
        self.action_export_brf = QAction(self.tr("Formato BR&F (.brf)"), self); self.action_export_brf.setToolTip(self.tr("Exporta el resultado Braille a un archivo compatible con impresoras Braille (.brf).")); self.action_export_brf.triggered.connect(self.export_as_brf)
        self.export_menu.addAction(self.action_export_brf)
        self.action_export_bra = QAction(self.tr("Formato B&RA (.bra)"), self); self.action_export_bra.setToolTip(self.tr("Exporta el resultado Braille a un archivo de texto Braille Unicode (.bra).")); self.action_export_bra.triggered.connect(self.export_as_bra)
        self.export_menu.addAction(self.action_export_bra)
        self.file_menu.addSeparator()

        self.action_print_braille = QAction(self.tr("Imprimir en Impresora Braille..."), self)
        self.action_print_braille.setToolTip(self.tr("Envía el texto Braille a una impresora Braille conectada."))
        self.action_print_braille.triggered.connect(self.open_braille_printer_dialog)
        self.file_menu.addAction(self.action_print_braille)

        self.file_menu.addSeparator()
        self.recent_files_menu = self.file_menu.addMenu(self.tr("Archivos Recientes"))
        self.file_menu.addSeparator()
        self.action_close = QAction(self.tr("&Cerrar"), self); self.action_close.setShortcut("Ctrl+Q"); self.action_close.setToolTip(self.tr("Cierra el archivo actual y limpia la interfaz.")); self.action_close.triggered.connect(self.close_file)
        self.file_menu.addAction(self.action_close)
        self.action_exit = QAction(self.tr("&Salir"), self); self.action_exit.setToolTip(self.tr("Cierra la aplicación.")); self.action_exit.triggered.connect(self.close)
        self.file_menu.addAction(self.action_exit)
        self.edit_menu = menu_bar.addMenu(self.tr("&Edición"))
        self.action_undo = QAction(self.tr("&Deshacer"), self)
        self.action_undo.setShortcut("Ctrl+Z")
        self.action_undo.setToolTip(self.tr("Deshace la última acción."))
        self.action_undo.triggered.connect(self.undo)
        self.edit_menu.addAction(self.action_undo)

        self.action_redo = QAction(self.tr("&Rehacer"), self)
        self.action_redo.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.action_redo.setToolTip(self.tr("Rehace la última acción deshecha."))
        self.action_redo.triggered.connect(self.redo)
        self.edit_menu.addAction(self.action_redo)

        self.edit_menu.addSeparator()

        self.action_copy = QAction(self.tr("&Copiar Braille al Portapapeles"), self)
        self.action_copy.setShortcut("Ctrl+C")
        self.action_copy.setToolTip(self.tr("Copia el contenido del panel de resultados al portapapeles."))
        self.action_copy.triggered.connect(self.copy_braille_to_clipboard)
        self.edit_menu.addAction(self.action_copy)

        self.action_drawing_mode = QAction(self.tr("Modo Dibujo Braille"), self)
        self.action_drawing_mode.setCheckable(True)
        self.action_drawing_mode.setToolTip(self.tr("Activa un lienzo para editar los puntos Braille directamente."))
        self.action_drawing_mode.triggered.connect(self._toggle_drawing_mode)
        self.edit_menu.addAction(self.action_drawing_mode)

        self.image_menu = menu_bar.addMenu(self.tr("&Imagen"))
        self.action_adjust = QAction(self.tr("&Brillo y Contraste"), self); self.action_adjust.setCheckable(True); self.action_adjust.setToolTip(self.tr("Muestra u oculta los controles de brillo y contraste.")); self.action_adjust.triggered.connect(self.toggle_adjustments_widget)
        self.image_menu.addAction(self.action_adjust)
        self.action_invert = QAction(self.tr("&Invertir Colores"), self); self.action_invert.setCheckable(True); self.action_invert.setToolTip(self.tr("Invierte los colores de la imagen (blanco a negro y viceversa).")); self.action_invert.triggered.connect(lambda: self.update_all_previews())
        self.image_menu.addAction(self.action_invert)
        self.action_dithering = QAction(self.tr("&Difuminado (Dithering)"), self); self.action_dithering.setCheckable(True); self.action_dithering.setToolTip(self.tr("Aplica un algoritmo de difuminado para simular sombras.")); self.action_dithering.triggered.connect(lambda: self.update_all_previews())
        self.image_menu.addAction(self.action_dithering)
        self.action_lines = QAction(self.tr("&Líneas"), self)
        self.action_lines.setCheckable(True)
        self.action_lines.setChecked(False)
        self.action_lines.setToolTip(self.tr("Activa el modo de detección de líneas en lugar de puntos.")); self.action_lines.triggered.connect(lambda: self.update_all_previews())
        
        self.action_adaptive_thresholding = QAction(self.tr("Umbral Adaptativo"), self)
        self.action_adaptive_thresholding.setCheckable(True)
        self.action_adaptive_thresholding.setToolTip(self.tr("Usa un umbral adaptativo en lugar de un umbral fijo."))
        self.action_adaptive_thresholding.triggered.connect(lambda: self.update_all_previews())
        self.image_menu.addAction(self.action_adaptive_thresholding)

        self.action_crop = QAction(self.tr("Recortar"), self)
        self.action_crop.setCheckable(True)
        self.action_crop.setToolTip(self.tr("Activa el modo de recorte para seleccionar un área de la imagen."))
        self.action_crop.triggered.connect(self._toggle_crop_mode)
        self.image_menu.addAction(self.action_crop)

        self.image_menu.addSeparator()

        self.algorithm_menu = self.image_menu.addMenu(self.tr("&Algoritmo"))

        self.edge_detection_group = QActionGroup(self)
        self.edge_detection_group.setExclusive(True)

        self.action_edge_none = QAction(self.tr("&Ninguno"), self)
        self.action_edge_none.setCheckable(True)
        self.action_edge_none.setChecked(True) # Default
        self.action_edge_none.triggered.connect(lambda: self.set_edge_detection_algorithm('none'))
        self.edge_detection_group.addAction(self.action_edge_none)
        self.algorithm_menu.addAction(self.action_edge_none)

        self.edge_detection_group.addAction(self.action_lines)
        self.algorithm_menu.addAction(self.action_lines)
        self.algorithm_menu.addSeparator()

        self.action_edge_canny = QAction(self.tr("&Canny"), self)
        self.action_edge_canny.setCheckable(True)
        self.action_edge_canny.triggered.connect(lambda: self.set_edge_detection_algorithm('canny'))
        self.edge_detection_group.addAction(self.action_edge_canny)
        self.algorithm_menu.addAction(self.action_edge_canny)

        self.action_edge_sobel = QAction(self.tr("&Sobel"), self)
        self.action_edge_sobel.setCheckable(True)
        self.action_edge_sobel.triggered.connect(lambda: self.set_edge_detection_algorithm('sobel'))
        self.edge_detection_group.addAction(self.action_edge_sobel)
        self.algorithm_menu.addAction(self.action_edge_sobel)

        self.action_edge_prewitt = QAction(self.tr("&Prewitt"), self)
        self.action_edge_prewitt.setCheckable(True)
        self.action_edge_prewitt.triggered.connect(lambda: self.set_edge_detection_algorithm('prewitt'))
        self.edge_detection_group.addAction(self.action_edge_prewitt)
        self.algorithm_menu.addAction(self.action_edge_prewitt)

        self.action_edge_laplacian = QAction(self.tr("&Laplacian"), self)
        self.action_edge_laplacian.setCheckable(True)
        self.action_edge_laplacian.triggered.connect(lambda: self.set_edge_detection_algorithm('laplacian'))
        self.edge_detection_group.addAction(self.action_edge_laplacian)
        self.algorithm_menu.addAction(self.action_edge_laplacian)

        self.action_remove_noise = QAction(self.tr("&Quitar Ruido"), self)
        self.action_remove_noise.setCheckable(True)
        self.action_remove_noise.setToolTip(self.tr("Aplica un filtro para eliminar el ruido de la imagen."))
        self.action_remove_noise.triggered.connect(self.remove_noise)
        self.image_menu.addAction(self.action_remove_noise)

        self.action_remove_noise = QAction(self.tr("&Quitar Ruido"), self)
        self.action_remove_noise.setCheckable(True)
        self.action_remove_noise.setToolTip(self.tr("Aplica un filtro para eliminar el ruido de la imagen."))
        self.action_remove_noise.triggered.connect(self.remove_noise)
        self.image_menu.addAction(self.action_remove_noise)

        self.image_menu.addSeparator()

        self.noise_reduction_menu = self.image_menu.addMenu(self.tr("&Reducción de Ruido"))

        self.noise_reduction_group = QActionGroup(self)
        self.noise_reduction_group.setExclusive(True)

        self.action_noise_none = QAction(self.tr("&Ninguno"), self)
        self.action_noise_none.setCheckable(True)
        self.action_noise_none.setChecked(True) # Default
        self.action_noise_none.triggered.connect(lambda: self.set_noise_reduction_filter('none'))
        self.noise_reduction_group.addAction(self.action_noise_none)
        self.noise_reduction_menu.addAction(self.action_noise_none)

        self.action_noise_median = QAction(self.tr("&Filtro Mediana"), self)
        self.action_noise_median.setCheckable(True)
        self.action_noise_median.triggered.connect(lambda: self.set_noise_reduction_filter('median'))
        self.noise_reduction_group.addAction(self.action_noise_median)
        self.noise_reduction_menu.addAction(self.action_noise_median)

        self.action_noise_gaussian = QAction(self.tr("&Filtro Gaussiano"), self)
        self.action_noise_gaussian.setCheckable(True)
        self.action_noise_gaussian.triggered.connect(lambda: self.set_noise_reduction_filter('gaussian'))
        self.noise_reduction_group.addAction(self.action_noise_gaussian)
        self.noise_reduction_menu.addAction(self.action_noise_gaussian)

        self.action_noise_bilateral = QAction(self.tr("&Filtro Bilateral"), self)
        self.action_noise_bilateral.setCheckable(True)
        self.action_noise_bilateral.triggered.connect(lambda: self.set_noise_reduction_filter('bilateral'))
        self.noise_reduction_group.addAction(self.action_noise_bilateral)
        self.noise_reduction_menu.addAction(self.action_noise_bilateral)

        self.image_menu.addSeparator()

        self.action_save_img_settings = QAction(self.tr("Guardar Ajustes de Imagen..."), self)
        self.action_save_img_settings.setToolTip(self.tr("Guarda los ajustes actuales de brillo, contraste, etc. en un archivo."))
        self.action_save_img_settings.triggered.connect(self.save_image_settings)
        self.image_menu.addAction(self.action_save_img_settings)

        self.image_menu.addSeparator()

        self.action_save_img_settings = QAction(self.tr("Guardar Ajustes de Imagen..."), self)
        self.action_save_img_settings.setToolTip(self.tr("Guarda los ajustes actuales de brillo, contraste, etc. en un archivo."))
        self.action_save_img_settings.triggered.connect(self.save_image_settings)
        self.image_menu.addAction(self.action_save_img_settings)

        self.action_load_img_settings = QAction(self.tr("Cargar Ajustes de Imagen..."), self)
        self.action_load_img_settings.setToolTip(self.tr("Carga ajustes de brillo, contraste, etc. desde un archivo."))
        self.action_load_img_settings.triggered.connect(self.load_image_settings)
        self.image_menu.addAction(self.action_load_img_settings)

        self.image_menu.addSeparator()

        self.segmentation_menu = self.image_menu.addMenu(self.tr("&Segmentación"))

        self.segmentation_group = QActionGroup(self)
        self.segmentation_group.setExclusive(True)

        self.action_segmentation_none = QAction(self.tr("&Ninguno"), self)
        self.action_segmentation_none.setCheckable(True)
        self.action_segmentation_none.setChecked(True) # Default
        self.action_segmentation_none.triggered.connect(lambda: self.set_segmentation_algorithm('none'))
        self.segmentation_group.addAction(self.action_segmentation_none)
        self.segmentation_menu.addAction(self.action_segmentation_none)

        self.action_segmentation_grabcut = QAction(self.tr("&GrabCut"), self)
        self.action_segmentation_grabcut.setCheckable(True)
        self.action_segmentation_grabcut.triggered.connect(lambda: self.set_segmentation_algorithm('grabcut'))
        self.segmentation_group.addAction(self.action_segmentation_grabcut)
        self.segmentation_menu.addAction(self.action_segmentation_grabcut)

        self.image_menu.addSeparator()

        self.action_convert_to_braille = QAction(self.tr("Convertir a Braille"), self)
        self.action_convert_to_braille.setToolTip(self.tr("Convierte la imagen actual a texto Braille."))
        self.action_convert_to_braille.triggered.connect(self.convert_image_to_braille_action)
        self.image_menu.addAction(self.action_convert_to_braille)

        self.image_menu.addSeparator()

        self.color_menu = self.image_menu.addMenu(self.tr("&Color"))

        self.color_mode_group = QActionGroup(self)
        self.color_mode_group.setExclusive(True)

        self.action_color_original = QAction(self.tr("&Original Color"), self)
        self.action_color_original.setCheckable(True)
        self.action_color_original.setChecked(True) # Default
        self.action_color_original.triggered.connect(lambda: self.set_color_mode('original'))
        self.color_mode_group.addAction(self.action_color_original)
        self.color_menu.addAction(self.action_color_original)

        self.action_color_grayscale = QAction(self.tr("&Grayscale"), self)
        self.action_color_grayscale.setCheckable(True)
        self.action_color_grayscale.triggered.connect(lambda: self.set_color_mode('grayscale'))
        self.color_mode_group.addAction(self.action_color_grayscale)
        self.color_menu.addAction(self.action_color_grayscale)

        self.color_menu.addSeparator()

        self.action_color_red = QAction(self.tr("&Rojo"), self)
        self.action_color_red.setCheckable(True)
        self.action_color_red.triggered.connect(lambda: self.toggle_color_filter('red', self.action_color_red.isChecked()))
        self.color_menu.addAction(self.action_color_red)

        self.action_color_green = QAction(self.tr("&Verde"), self)
        self.action_color_green.setCheckable(True)
        self.action_color_green.triggered.connect(lambda: self.toggle_color_filter('green', self.action_color_green.isChecked()))
        self.color_menu.addAction(self.action_color_green)

        self.action_color_blue = QAction(self.tr("&Azul"), self)
        self.action_color_blue.setCheckable(True)
        self.action_color_blue.triggered.connect(lambda: self.toggle_color_filter('blue', self.action_color_blue.isChecked()))
        self.color_menu.addAction(self.action_color_blue)

        self.image_menu.addSeparator()

        self.image_menu.addSeparator()

        self.action_describe_image = QAction(self.tr("Describir Imagen con Gemini"), self)
        self.action_describe_image.triggered.connect(self.describe_image_with_gemini)
        self.image_menu.addAction(self.action_describe_image)

        self.action_compare_images = QAction(self.tr("Comparar Imágenes"), self)
        self.action_compare_images.triggered.connect(self.compare_images)
        self.image_menu.addAction(self.action_compare_images)

        self.action_zoom_in_image = QAction(self.tr("Aumentar Zoom Imagen"), self)
        self.action_zoom_in_image.setShortcut("Ctrl++")
        self.action_zoom_in_image.setToolTip(self.tr("Aumenta el zoom de la imagen."))
        self.action_zoom_in_image.triggered.connect(self.zoom_in)
        self.image_menu.addAction(self.action_zoom_in_image)

        self.action_zoom_out_image = QAction(self.tr("Reducir Zoom Imagen"), self)
        self.action_zoom_out_image.setShortcut("Ctrl+-")
        self.action_zoom_out_image.setToolTip(self.tr("Reduce el zoom de la imagen."))
        self.action_zoom_out_image.triggered.connect(self.zoom_out)
        self.image_menu.addAction(self.action_zoom_out_image)

        self.braille_menu = menu_bar.addMenu(self.tr("&Braille"))
        self.action_desbraille = QAction(self.tr("&Desbraillar"), self); self.action_desbraille.setToolTip(self.tr("Convierte el texto Braille de vuelta a texto plano (tinta).")); self.action_desbraille.triggered.connect(self.desbraille_braille_text)
        self.braille_menu.addAction(self.action_desbraille)
        self.action_no_split_words = QAction(self.tr("No &partir palabras"), self); self.action_no_split_words.setCheckable(True); self.action_no_split_words.setToolTip(self.tr("Evita que las palabras se dividan al final de una línea en la salida Braille."))
        self.action_no_split_words.setChecked(False)
        self.action_no_split_words.triggered.connect(self.reformat_braille_output)
        self.braille_menu.addAction(self.action_no_split_words)

        self.braille_menu.addSeparator()

        self.action_visualize_braille = QAction(self.tr("&Visualizar Braille"), self); self.action_visualize_braille.setToolTip(self.tr("Convierte el texto Braille en una imagen visual de los puntos.")); self.action_visualize_braille.triggered.connect(self.visualize_braille_text)
        self.braille_menu.addAction(self.action_visualize_braille)

        self.action_braille_cell_editor = QAction(self.tr("&Editor de Celdas Braille"), self); self.action_braille_cell_editor.setToolTip(self.tr("Abre un editor para crear o modificar caracteres Braille de forma interactiva.")); self.action_braille_cell_editor.triggered.connect(self.open_braille_text_editor)
        self.braille_menu.addAction(self.action_braille_cell_editor)

        self.action_interactive_learning = QAction(self.tr("&Modo de Aprendizaje Interactivo"), self)
        self.action_interactive_learning.setToolTip(self.tr("Abre un modo interactivo para aprender Braille."))
        self.action_interactive_learning.triggered.connect(self.open_braille_learning_dialog)
        self.braille_menu.addAction(self.action_interactive_learning)

        self.braille_menu.addSeparator()

        self.action_zoom_in_braille = QAction(self.tr("Aumentar Zoom Braille"), self)
        self.action_zoom_in_braille.setShortcut("Ctrl+Shift++")
        self.action_zoom_in_braille.setToolTip(self.tr("Aumenta el tamaño de la fuente del texto Braille."))
        self.action_zoom_in_braille.triggered.connect(self.zoom_in_text)
        self.braille_menu.addAction(self.action_zoom_in_braille)

        self.action_zoom_out_braille = QAction(self.tr("Reducir Zoom Braille"), self)
        self.action_zoom_out_braille.setShortcut("Ctrl+Shift+-")
        self.action_zoom_out_braille.setToolTip(self.tr("Reduce el tamaño de la fuente del texto Braille."))
        self.action_zoom_out_braille.triggered.connect(self.zoom_out_text)
        self.braille_menu.addAction(self.action_zoom_out_braille)
        
        self.braille_menu.addSeparator()
        
        dots_group = QActionGroup(self)
        self.action_6_dots = QAction(self.tr("&6 puntos"), self)
        self.action_6_dots.setCheckable(True)
        self.action_6_dots.setChecked(True)  # Default
        self.action_6_dots.setToolTip(self.tr("Establece el modo de conversión a Braille de 6 puntos."))
        self.action_6_dots.triggered.connect(lambda: self.set_braille_dots_mode(6))
        dots_group.addAction(self.action_6_dots)
        self.braille_menu.addAction(self.action_6_dots)

        self.action_8_dots = None
        try:
            self.action_8_dots = QAction(self.tr("&8 puntos"), self)
            self.action_8_dots.setCheckable(True)
            self.action_8_dots.setToolTip(self.tr("Establece el modo de conversión a Braille de 8 puntos (informático)."))
            self.action_8_dots.triggered.connect(lambda: self.set_braille_dots_mode(8))
            dots_group.addAction(self.action_8_dots)
            self.braille_menu.addAction(self.action_8_dots)
        except Exception as e:
            print(f"Error creating action_8_dots: {e}")

        self.math_menu = menu_bar.addMenu(self.tr("&Matemáticas"))

        self.function_menu = self.math_menu.addMenu(self.tr("&Función"))

        self.action_linear_function = QAction(self.tr("&Lineal"), self)
        self.action_linear_function.triggered.connect(self.open_linear_function_dialog)
        self.function_menu.addAction(self.action_linear_function)

        self.action_quadratic_function = QAction(self.tr("&Cuadrática"), self)
        self.action_quadratic_function.triggered.connect(self.open_quadratic_function_dialog)
        self.function_menu.addAction(self.action_quadratic_function)

        self.action_cubic_function = QAction(self.tr("&Cúbica"), self)
        self.action_cubic_function.triggered.connect(self.open_cubic_function_dialog)
        self.function_menu.addAction(self.action_cubic_function)

        self.action_polynomial_function = QAction(self.tr("&Polinómica"), self)
        self.action_polynomial_function.setShortcut("Ctrl+M")
        self.action_polynomial_function.triggered.connect(self.open_polynomial_function_dialog)
        self.function_menu.addAction(self.action_polynomial_function)

        self.action_composite_function = QAction(self.tr("Compuesta"), self)
        self.action_composite_function.setShortcut("Ctrl+Shift+C")
        self.action_composite_function.triggered.connect(self.open_composite_function_dialog)
        self.function_menu.addAction(self.action_composite_function)

        self.function_menu.addSeparator()

        self.action_analyze_function = QAction(self.tr("Analizar Función"), self)
        self.action_analyze_function.triggered.connect(self.open_function_analysis_dialog)
        self.function_menu.addAction(self.action_analyze_function)



        self.math_menu.addSeparator()

        self.action_points_graph = QAction(self.tr("Graficar &Puntos"), self)
        self.action_points_graph.triggered.connect(self.open_points_graph_dialog)
        self.math_menu.addAction(self.action_points_graph)

        self.math_menu.addSeparator()

        self.action_show_equation = QAction(self.tr("&Mostrar Ecuación"), self)
        self.action_show_equation.setCheckable(True)
        self.action_show_equation.setChecked(True) # Default to showing equation
        self.action_show_equation.triggered.connect(self.toggle_show_equation)
        self.math_menu.addAction(self.action_show_equation)

        self.action_show_roots = QAction(self.tr("&Mostrar Raíces"), self)
        self.action_show_roots.setCheckable(True)
        self.action_show_roots.setChecked(True) # Default to showing roots
        self.action_show_roots.triggered.connect(self.toggle_show_roots)
        self.math_menu.addAction(self.action_show_roots)

        # Settings Menu
        self.settings_menu = menu_bar.addMenu(self.tr("&Configuración"))
        self.language_menu = self.settings_menu.addMenu(self.tr("&Idioma"))
        
        self.lang_group = QActionGroup(self)
        self.lang_group.setExclusive(True)

        # Predefined languages
        self.action_lang_es = QAction(self.tr("&Castellano"), self)
        self.action_lang_es.setCheckable(True)
        self.action_lang_es.triggered.connect(lambda: self.set_language('es'))
        self.lang_group.addAction(self.action_lang_es)
        self.language_menu.addAction(self.action_lang_es)

        self.action_lang_ca = QAction(self.tr("&Català"), self)
        self.action_lang_ca.setCheckable(True)
        self.action_lang_ca.triggered.connect(lambda: self.set_language('ca'))
        self.lang_group.addAction(self.action_lang_ca)
        self.language_menu.addAction(self.action_lang_ca)

        self.action_lang_eu = QAction(self.tr("&Euskara"), self)
        self.action_lang_eu.setCheckable(True)
        self.action_lang_eu.triggered.connect(lambda: self.set_language('eu'))
        self.lang_group.addAction(self.action_lang_eu)
        self.language_menu.addAction(self.action_lang_eu)

        self.action_lang_gl = QAction(self.tr("&Galego"), self)
        self.action_lang_gl.setCheckable(True)
        self.action_lang_gl.triggered.connect(lambda: self.set_language('gl'))
        self.lang_group.addAction(self.action_lang_gl)
        self.language_menu.addAction(self.action_lang_gl)

        self.action_lang_en = QAction(self.tr("&English"), self)
        self.action_lang_en.setCheckable(True)
        self.action_lang_en.triggered.connect(lambda: self.set_language('en'))
        self.lang_group.addAction(self.action_lang_en)
        self.language_menu.addAction(self.action_lang_en)

        self.language_menu.addSeparator()
        self.custom_language_actions = [] # To store actions for custom tables
        self.update_language_menu() # Initial population of language menu

        # Custom Braille Tables
        self.action_manage_braille_tables = QAction(self.tr("Gestionar Tablas Braille Personalizadas..."), self)
        self.action_manage_braille_tables.triggered.connect(self.open_custom_braille_table_dialog)
        self.settings_menu.addAction(self.action_manage_braille_tables)

        # Theme Menu
        self.theme_menu = self.settings_menu.addMenu(self.tr("&Tema"))
        self.theme_group = QActionGroup(self)

        self.action_theme_system = QAction(self.tr("&Sistema"), self)
        self.action_theme_system.setCheckable(True)
        self.action_theme_system.triggered.connect(lambda: self.set_theme('system'))
        self.theme_group.addAction(self.action_theme_system)
        self.theme_menu.addAction(self.action_theme_system)

        self.action_theme_dark = QAction(self.tr("&Oscuro"), self)
        self.action_theme_dark.setCheckable(True)
        self.action_theme_dark.triggered.connect(lambda: self.set_theme('dark'))
        self.theme_group.addAction(self.action_theme_dark)
        self.theme_menu.addAction(self.action_theme_dark)

        self.action_theme_light = QAction(self.tr("&Claro"), self)
        self.action_theme_light.setCheckable(True)
        self.action_theme_light.triggered.connect(lambda: self.set_theme('light'))
        self.theme_group.addAction(self.action_theme_light)
        self.theme_menu.addAction(self.action_theme_light)

        self.action_theme_high_contrast = QAction(self.tr("&Alto Contraste"), self)
        self.action_theme_high_contrast.setCheckable(True)
        self.action_theme_high_contrast.triggered.connect(lambda: self.set_theme('high_contrast'))
        self.theme_group.addAction(self.action_theme_high_contrast)
        self.theme_menu.addAction(self.action_theme_high_contrast)

        # Font Size Menu
        self.font_size_menu = self.settings_menu.addMenu(self.tr("Tamaño &Fuente"))
        self.font_size_group = QActionGroup(self)

        self.action_font_size_system = QAction(self.tr("&Sistema"), self)
        self.action_font_size_system.setCheckable(True)
        self.action_font_size_system.triggered.connect(lambda: self.set_font_size('system'))
        self.font_size_group.addAction(self.action_font_size_system)
        self.font_size_menu.addAction(self.action_font_size_system)

        self.action_font_size_14 = QAction(self.tr("&14 puntos"), self)
        self.action_font_size_14.setCheckable(True)
        self.action_font_size_14.triggered.connect(lambda: self.set_font_size(14))
        self.font_size_group.addAction(self.action_font_size_14)
        self.font_size_menu.addAction(self.action_font_size_14)

        self.action_font_size_16 = QAction(self.tr("&16 puntos"), self)
        self.action_font_size_16.setCheckable(True)
        self.action_font_size_16.triggered.connect(lambda: self.set_font_size(16))
        self.font_size_group.addAction(self.action_font_size_16)
        self.font_size_menu.addAction(self.action_font_size_16)

        self.action_font_size_18 = QAction(self.tr("&18 puntos"), self)
        self.action_font_size_18.setCheckable(True)
        self.action_font_size_18.triggered.connect(lambda: self.set_font_size(18))
        self.font_size_group.addAction(self.action_font_size_18)
        self.font_size_menu.addAction(self.action_font_size_18)

        self.action_font_size_22 = QAction(self.tr("&22 puntos"), self)
        self.action_font_size_22.setCheckable(True)
        self.action_font_size_22.triggered.connect(lambda: self.set_font_size(22))
        self.font_size_group.addAction(self.action_font_size_22)
        self.font_size_menu.addAction(self.action_font_size_22)

        self.action_font_size_32 = QAction(self.tr("&32 puntos"), self)
        self.action_font_size_32.setCheckable(True)
        self.action_font_size_32.triggered.connect(lambda: self.set_font_size(32))
        self.font_size_group.addAction(self.action_font_size_32)
        self.font_size_menu.addAction(self.action_font_size_32)

        self.help_menu = menu_bar.addMenu(self.tr("&Ayuda"))
        self.action_show_shortcuts = QAction(self.tr("&Atajos de Teclado..."), self)
        self.action_show_shortcuts.setToolTip(self.tr("Muestra una lista de los atajos de teclado disponibles."))
        self.action_show_shortcuts.triggered.connect(self.show_shortcuts_dialog)
        self.help_menu.addAction(self.action_show_shortcuts)

    def compare_images(self):
        if self.original_cv_img is None or not self.raw_braille_text:
            QMessageBox.warning(self, self.tr("Sin imagen o Braille"), self.tr("Carga una imagen y conviértela a Braille antes de comparar."))
            return

        try:
            # 1. Get the original image with edges
            edges = cv2.Canny(self.original_cv_img, 100, 200)
            is_success, buffer_edges = cv2.imencode(".jpg", edges)
            if not is_success:
                QMessageBox.critical(self, self.tr("Error de Conversión"), self.tr("No se pudo convertir la imagen de bordes a formato JPG."))
                return
            image_bytes_1 = buffer_edges.tobytes()

            # 2. Generate an image from the Braille text
            braille_image = self.visualize_braille_text(to_bytes=True)
            if not braille_image:
                return

            # 3. Get Gemini API Key from user
            api_key, ok = QInputDialog.getText(self, self.tr("API Key de Gemini"), self.tr("Introduce tu API Key de Google AI:"))
            if not ok or not api_key:
                return

            # 4. Initialize GeminiClient and compare the images
            gemini = GeminiClient(api_key=api_key)
            prompt = "Compare the two images. The first image contains the edges of an original drawing, and the second image is its Braille representation. Analyze if the most important lines of the original drawing have been transformed and coincide with the Braille version. Provide a percentage of coincidence."
            coincidence_percentage = gemini.compare_images(image_bytes_1, braille_image, prompt)

            # 5. Display the result
            QMessageBox.information(self, self.tr("Resultado de la Comparación"), f"{self.tr('Porcentaje de coincidencia:')} {coincidence_percentage}")

        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))


    def describe_image_with_gemini(self):
        if self.original_cv_img is None:
            QMessageBox.warning(self, self.tr("Sin imagen"), self.tr("Carga una imagen antes de describirla."))
            return

        try:
            # Convert the OpenCV image to bytes
            is_success, buffer = cv2.imencode(".jpg", self.original_color_cv_img)
            if not is_success:
                QMessageBox.critical(self, self.tr("Error de Conversión"), self.tr("No se pudo convertir la imagen a formato JPG."))
                return

            image_bytes = buffer.tobytes()

            # Get Gemini API Key from user
            api_key, ok = QInputDialog.getText(self, self.tr("API Key de Gemini"), self.tr("Introduce tu API Key de Google AI:"))
            if not ok or not api_key:
                return

            # Initialize GeminiClient and describe the image
            gemini = GeminiClient(api_key=api_key)
            description = gemini.describe_image(image_bytes)

            # Display the description
            QMessageBox.information(self, self.tr("Descripción de la Imagen"), description)

        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def remove_graph_dialog(self, dialog):
        if dialog in self.open_graph_dialogs:
            self.open_graph_dialogs.remove(dialog)

    def close_graph_tab(self, index):
        widget = self.graph_tabs.widget(index)
        if widget is not None:
            widget.deleteLater()
        self.graph_tabs.removeTab(index)
        if self.graph_tabs.count() == 0:
            self.graph_tabs.setVisible(False)



    def set_noise_reduction_filter(self, filter_type):
        """Establece el filtro de reducción de ruido y actualiza la UI."""
        self.current_noise_reduction_filter = filter_type
        logging.info(f"Filtro de reducción de ruido cambiado a: {filter_type}")

        # Muestra el panel de ajustes apropiado
        self.filter_settings_panel.show_filter_group(filter_type)

        self.update_all_previews()
        self._save_state()

    def set_edge_detection_algorithm(self, algorithm):
        """Establece el algoritmo de detección de bordes y actualiza la UI."""
        self.current_edge_detection_algorithm = algorithm
        logging.info(f"Algoritmo de detección de bordes cambiado a: {algorithm}")
        
        # Muestra el panel de ajustes apropiado
        self.filter_settings_panel.show_filter_group(algorithm)

        self.update_all_previews()
        self._save_state()

    def create_ui_widgets(self):
        self.image_mode_widgets = []
        self.braille_mode_widgets = []

        # Main vertical layout
        self.content_layout = QVBoxLayout()
        self.main_layout.addLayout(self.content_layout)

        # Contenedor principal para poder cambiar entre vistas (normal y dibujo)
        self.view_stack = QStackedWidget()
        self.content_layout.addWidget(self.view_stack)

        # Vista normal (la que ya existía)
        self.normal_view_widget = QWidget()
        self.normal_view_layout = QVBoxLayout(self.normal_view_widget)
        self.view_stack.addWidget(self.normal_view_widget)


        # Top side: Image preview and its controls
        self.left_panel_widget = QWidget()
        self.left_panel_layout = QVBoxLayout(self.left_panel_widget)
        self.normal_view_layout.addWidget(self.left_panel_widget, 1) # Stretch factor 1 for 50% width

        self.adjustments_widget = QWidget(); self.adjustments_widget.setMaximumWidth(600)
        adjustments_layout = QGridLayout()
        self.slider_brightness = QSlider(Qt.Horizontal); self.slider_brightness.setRange(-100, 100); self.slider_brightness.setValue(0); self.slider_brightness.setToolTip(self.tr("Ajusta el brillo")); self.slider_brightness.valueChanged.connect(self.update_image_preview); self.slider_brightness.sliderReleased.connect(self.update_braille_output)
        self.slider_brightness.setAccessibleName(self.tr("Deslizador de brillo"))
        self.slider_brightness.setAccessibleDescription(self.tr("Aumenta o disminuye el brillo de la imagen."))
        self.lbl_brightness_value = QLabel("0")
        self.slider_contrast = QSlider(Qt.Horizontal); self.slider_contrast.setRange(1, 400); self.slider_contrast.setValue(100); self.slider_contrast.setToolTip(self.tr("Ajusta el contraste")); self.slider_contrast.valueChanged.connect(self.update_image_preview); self.slider_contrast.sliderReleased.connect(self.update_braille_output)
        self.slider_contrast.setAccessibleName(self.tr("Deslizador de contraste"))
        self.slider_contrast.setAccessibleDescription(self.tr("Aumenta o disminuye el contraste de la imagen."))
        self.lbl_contrast_value = QLabel("1.00")
        adjustments_layout.addWidget(QLabel(self.tr("Brillo:")), 0, 0); adjustments_layout.addWidget(self.slider_brightness, 0, 1); adjustments_layout.addWidget(self.lbl_brightness_value, 0, 2)
        adjustments_layout.addWidget(QLabel(self.tr("Contraste:")), 1, 0); adjustments_layout.addWidget(self.slider_contrast, 1, 1); adjustments_layout.addWidget(self.lbl_contrast_value, 1, 2)
        self.adjustments_widget.setLayout(adjustments_layout)
        self.left_panel_layout.addWidget(self.adjustments_widget)

        # Panel de ajustes de filtros
        self.filter_settings_panel = FilterSettingsPanel(self)
        self.left_panel_layout.addWidget(self.filter_settings_panel)
        self.filter_settings_panel.parameters_changed.connect(self.update_image_preview)

        self.scroll_area_img = QScrollArea(); self.scroll_area_img.setWidgetResizable(True)
        self.lbl_image_preview = ImageLabel(self.tr("Arrastra una imagen aquí o cárgala desde el menú Archivo")); self.lbl_image_preview.setAlignment(Qt.AlignCenter)
        self.scroll_area_img.setWidget(self.lbl_image_preview)
        self.lbl_image_preview.new_selection.connect(self._on_new_crop_selection)
        self.lbl_image_preview.selection_cleared.connect(self._on_crop_selection_cleared)
        self.left_panel_layout.addWidget(self.scroll_area_img)
        self.image_mode_widgets.append(self.scroll_area_img)



        # Bottom side: Braille output and its controls
        self.right_panel_widget = QWidget()
        self.right_panel_layout = QVBoxLayout(self.right_panel_widget)
        self.normal_view_layout.addWidget(self.right_panel_widget, 1) # Stretch factor 1 for 50% width

        # Graph Tabs
        self.graph_tabs = QTabWidget()
        self.graph_tabs.setTabsClosable(True)
        self.graph_tabs.tabCloseRequested.connect(self.close_graph_tab)
        self.normal_view_layout.addWidget(self.graph_tabs)
        self.graph_tabs.setVisible(False) # Initially hidden

        # Braille output and its controls
        self.braille_output_container = QWidget()
        braille_output_layout = QVBoxLayout(self.braille_output_container)
        self.braille_display = QTextEdit(); self.braille_display.setPlaceholderText(self.tr("El resultado en Braille aparecerá aquí...")); self.braille_display.setReadOnly(True); self.braille_display.setFont(QFont("Courier New", 10))
        self.braille_display.setAccessibleName(self.tr("Salida de texto Braille"))
        self.braille_display.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.braille_display.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.braille_display.setMinimumSize(200, 200) # Set a minimum size
        braille_output_layout.addWidget(self.braille_display)

        self.latin_display = QTextEdit(); self.latin_display.setPlaceholderText(self.tr("El texto en tinta aparecerá aquí...")); self.latin_display.setReadOnly(True); self.latin_display.setFont(QFont("Arial", 10))
        self.latin_display.setAccessibleName(self.tr("Salida de texto plano (tinta)"))
        braille_output_layout.addWidget(self.latin_display)
        self.right_panel_layout.addWidget(self.braille_output_container)
        self.braille_mode_widgets.append(self.braille_output_container)



        # Braille Display Settings Widget
        self.braille_settings_widget = QWidget()
        braille_settings_layout = QGridLayout()

        self.slider_dot_size = QSlider(Qt.Horizontal)
        self.slider_dot_size.setRange(1, 10)
        self.slider_dot_size.setValue(self.braille_dot_size)
        self.slider_dot_size.setToolTip(self.tr("Ajusta el tamaño de los puntos Braille"))
        self.slider_dot_size.valueChanged.connect(self.update_braille_display_settings)
        self.slider_dot_size.setAccessibleName(self.tr("Deslizador de tamaño de punto Braille"))
        self.lbl_dot_size_value = QLabel(str(self.braille_dot_size))

        self.slider_dot_spacing = QSlider(Qt.Horizontal)
        self.slider_dot_spacing.setRange(0, 5)
        self.slider_dot_spacing.setValue(self.braille_dot_spacing)
        self.slider_dot_spacing.setToolTip(self.tr("Ajusta el espaciado entre puntos Braille"))
        self.slider_dot_spacing.valueChanged.connect(self.update_braille_display_settings)
        self.slider_dot_spacing.setAccessibleName(self.tr("Deslizador de espaciado de punto Braille"))
        self.lbl_dot_spacing_value = QLabel(str(self.braille_dot_spacing))

        braille_settings_layout.addWidget(QLabel(self.tr("Tamaño del Punto:")), 0, 0)
        braille_settings_layout.addWidget(self.slider_dot_size, 0, 1)
        braille_settings_layout.addWidget(self.lbl_dot_size_value, 0, 2)

        braille_settings_layout.addWidget(QLabel(self.tr("Espaciado del Punto:")), 1, 0)
        braille_settings_layout.addWidget(self.slider_dot_spacing, 1, 1)
        braille_settings_layout.addWidget(self.lbl_dot_spacing_value, 1, 2)

        # Color Scheme Buttons
        self.btn_default_colors = QPushButton(self.tr("Colores por Defecto"))
        self.btn_default_colors.clicked.connect(lambda: self.set_braille_color_scheme('default'))
        self.btn_default_colors.setAccessibleName(self.tr("Esquema de colores por defecto"))
        braille_settings_layout.addWidget(self.btn_default_colors, 2, 0, 1, 3)

        self.btn_inverted_colors = QPushButton(self.tr("Colores Invertidos"))
        self.btn_inverted_colors.clicked.connect(lambda: self.set_braille_color_scheme('inverted'))
        self.btn_inverted_colors.setAccessibleName(self.tr("Esquema de colores invertidos"))
        braille_settings_layout.addWidget(self.btn_inverted_colors, 3, 0, 1, 3)

        self.braille_settings_widget.setLayout(braille_settings_layout)
        self.right_panel_layout.addWidget(self.braille_settings_widget)
        self.braille_settings_widget.setVisible(False) # Initially hidden

        # --- Vista de Dibujo Braille ---
        self.drawing_view_widget = QWidget()
        self.drawing_view_layout = QVBoxLayout(self.drawing_view_widget)
        
        # Barra de herramientas de dibujo
        self.drawing_toolbar = DrawingToolbar()
        self.drawing_toolbar.tool_selected.connect(self.set_drawing_tool)
        self.drawing_toolbar.setVisible(False) # Oculta al inicio
        self.main_layout.insertWidget(0, self.drawing_toolbar) # Insertar antes del view_stack

        # Lienzo de dibujo Braille
        self.braille_canvas = BrailleCanvas()
        self.braille_canvas.content_changed.connect(self._on_canvas_changed)
        canvas_scroll_area = QScrollArea()
        canvas_scroll_area.setWidgetResizable(True)
        canvas_scroll_area.setWidget(self.braille_canvas)
        self.drawing_view_layout.addWidget(canvas_scroll_area)

        self.view_stack.addWidget(self.drawing_view_widget)

    def enable_initial_actions(self, enabled):
        self.action_open_image.setEnabled(enabled)
        self.action_open_text.setEnabled(enabled)
        self.action_batch_process.setEnabled(enabled)
        for action in [self.action_save, self.action_copy, self.export_menu, self.action_adjust, self.action_invert, self.action_dithering, self.action_lines, self.action_adaptive_thresholding, self.action_remove_noise, self.action_convert_to_braille, self.action_zoom_in_image, self.action_zoom_out_image, self.action_desbraille, self.action_no_split_words, self.action_visualize_braille, self.action_zoom_in_braille, self.action_zoom_out_braille, self.action_save_img_settings, self.action_load_img_settings, self.action_print_braille]: action.setEnabled(False)

        self.adjustments_widget.setVisible(False)
        self.braille_settings_widget.setVisible(False)
        self.latin_display.setVisible(False)
        self.left_panel_widget.setVisible(False)
        self.right_panel_widget.setVisible(False)

    def set_ui_mode(self, mode):
        is_image_mode = (mode == 'image')
        is_text_mode = (mode == 'text')
        is_braille_file_mode = (mode == 'braille_file')
        is_initial_state = (mode == 'initial_state')

        # Image related widgets
        self.left_panel_widget.setVisible(is_image_mode)

        self.adjustments_widget.setVisible(is_image_mode and (self.original_cv_img is not None and self.original_cv_img.size > 0))

        # Braille/Text related widgets
        self.right_panel_widget.setVisible(is_image_mode or is_text_mode or is_braille_file_mode)
        self.braille_output_container.setVisible(is_image_mode or is_text_mode or is_braille_file_mode)
        self.braille_settings_widget.setVisible(is_text_mode or is_braille_file_mode)
        self.latin_display.setVisible(False) # Initially hidden, shown by 'Desbraillar'

        # Enable/Disable actions based on mode
        self.action_adjust.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_invert.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_dithering.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_lines.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_adaptive_thresholding.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_remove_noise.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_convert_to_braille.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_zoom_in_image.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_zoom_out_image.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_save_img_settings.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_load_img_settings.setEnabled(is_image_mode and self.original_cv_img is not None)
        self.action_desbraille.setEnabled(is_text_mode or is_braille_file_mode)
        self.action_no_split_words.setEnabled(is_text_mode or is_braille_file_mode)
        self.action_visualize_braille.setEnabled(is_text_mode or is_braille_file_mode)
        has_content = bool(self.braille_display.toPlainText())
        self.action_zoom_in_braille.setEnabled(has_content and (is_text_mode or is_braille_file_mode))
        self.action_zoom_out_braille.setEnabled(has_content and (is_text_mode or is_braille_file_mode))
        self.action_braille_cell_editor.setEnabled(has_content)

        # Font settings
        if is_text_mode or is_braille_file_mode:
            self.braille_display.setFont(QFont("Courier New", 10))
            self.latin_display.setFont(QFont("Arial", 10))
        

    @gui_error_handler
    def open_image_dialog(self):
        logging.info("Abriendo diálogo para seleccionar imagen.")
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen", "", f"Archivos de Imagen (*{' *'.join(self.supported_image_extensions)})")
        if file_path: 
            self.load_image(file_path)
        else:
            logging.info("El usuario canceló la selección de imagen.")

    @gui_error_handler
    def open_text_dialog(self):
        logging.info("Abriendo diálogo para seleccionar texto.")
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Seleccionar Texto"), "", self.tr("Documentos de Texto (*.txt *.docx *.pdf *.rtf *.odt)"))
        if file_path:
            _, extension = os.path.splitext(file_path)
            supported_text_extensions = [".txt", ".docx", ".pdf", ".rtf", ".odt"]
            if extension.lower() not in supported_text_extensions:
                QMessageBox.critical(self, self.tr("Tipo de Archivo no Soportado"), self.tr(f"La extensión de archivo '{extension}' no es soportada para texto."))
                return
            self.load_text(file_path, is_file=True)
        else:
            logging.info("El usuario canceló la selección de texto.")

    @gui_error_handler
    def load_image(self, file_path):
        logging.info(f"Iniciando carga de imagen: {file_path}")
        _, extension = os.path.splitext(file_path)
        if extension.lower() not in self.supported_image_extensions:
            QMessageBox.critical(self, self.tr("Tipo de Archivo no Soportado"), self.tr(f"La extensión de archivo '{extension}' no es soportada."))
            logging.warning(f"Intento de cargar tipo de archivo de imagen no soportado: {extension}")
            return

        try:
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error de Lectura de Archivo"), self.tr(f"No se pudo leer el archivo de imagen: {os.path.basename(file_path)}. Error: {e}"))
            logging.error(f"Error al leer el archivo de imagen {file_path}: {e}", exc_info=True)
            return

        worker = Worker(self._load_image_task, image_bytes, file_path)
        worker.signals.result.connect(self._on_load_image_result)
        worker.signals.finished.connect(self._task_complete)
        worker.signals.error.connect(self._task_error)
        worker.signals.progress.connect(self.update_progress)
        self.threadpool.start(worker)
        self.statusBar().showMessage(self.tr("Cargando imagen..."), 0)

    def _load_image_task(self, image_bytes, original_file_path, progress_callback):
        logging.info(f"_load_image_task: Intentando cargar imagen desde bytes (original: {original_file_path})")
        progress_callback.emit(10, self.tr("Leyendo datos de imagen..."))

        try:
            if original_file_path.lower().endswith('.svg'):
                logging.info("Detectado archivo SVG, iniciando renderizado.")
                renderer = QSvgRenderer(image_bytes)
                if not renderer.isValid():
                    raise ValueError("El contenido del SVG no es válido.")

                size = renderer.defaultSize()
                # Aumentar la resolución para una mejor calidad, si el SVG es muy pequeño
                if size.width() < 256:
                    size.setWidth(256)
                if size.height() < 256:
                    size.setHeight(256)

                q_image = QImage(size, QImage.Format_ARGB32)
                q_image.fill(Qt.transparent)
                
                painter = QPainter(q_image)
                renderer.render(painter)
                painter.end()

                # Convertir QImage a np.array (OpenCV)
                ptr = q_image.constBits()
                ptr.setsize(q_image.sizeInBytes())
                arr = np.array(ptr).reshape(q_image.height(), q_image.width(), 4) # ARGB
                
                # Convertir de ARGB (Qt) a BGR (OpenCV)
                color_img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
                img = cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)

            else:
                # Lógica existente para imágenes de mapa de bits
                np_arr = np.frombuffer(image_bytes, np.uint8)
                color_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR) # Cargar en color
                if color_img is None:
                    raise IOError(self.tr(f"No se pudo decodificar la imagen. El archivo puede estar corrupto o en un formato no soportado: {os.path.basename(original_file_path)}"))
                img = cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY) # Convertir a escala de grises para procesado

        except Exception as e:
            raise IOError(self.tr(f"No se pudo procesar la imagen: {os.path.basename(original_file_path)}. Error: {e}"))

        if img is None:
            raise IOError(self.tr(f"No se pudo decodificar la imagen. El archivo puede estar corrupto o en un formato no soportado: {os.path.basename(original_file_path)}"))
        
        progress_callback.emit(100, self.tr("Imagen leída."))
        return img, color_img, original_file_path

    def _on_load_image_result(self, result):
        img, color_img, file_path = result
        if img is None:
            # This case should now be handled by the exception in the task
            return

        logging.info(f"Imagen cargada exitosamente: {file_path}")
        self.add_to_recent_files(file_path)
        self.original_cv_img = img
        self.original_color_cv_img = color_img
        self.image_path = file_path
        self.set_ui_mode('image')
        for action in [self.action_invert, self.action_dithering, self.action_adjust, self.action_adaptive_thresholding]:
            action.setChecked(False)
        self.action_remove_noise.setChecked(False)
        self.set_color_mode('original')
        self.slider_brightness.setValue(0)
        self.slider_contrast.setValue(100)
        self.adjustments_widget.setVisible(False)
        for action in [self.action_save, self.action_copy, self.export_menu]:
            action.setEnabled(True)
        self.fit_to_window()
        self._save_state()
        self.statusBar().showMessage(self.tr("Imagen cargada."), 3000)

    @gui_error_handler
    def load_text(self, content, is_file=True, language=None):
        logging.info(f"Iniciando carga de texto. Es un archivo: {is_file}")
        if language is None:
            items = [self.tr("Castellano Grado 1"), self.tr("Catalán Grado 1")]
            for table_name in self.custom_braille_tables.keys():
                items.append(table_name)

            item, ok = QInputDialog.getItem(self, self.tr("Seleccionar Tabla Braille"), self.tr("Elige la tabla de conversión:"), items, 0, False)
            if not ok or not item:
                logging.info("El usuario canceló la selección de tabla de conversión.")
                return
            
            if item == self.tr("Castellano Grado 1"):
                language = 'spanish'
            elif item == self.tr("Catalán Grado 1"):
                language = 'catalan'
            else:
                language = item
        
        worker = Worker(self._load_text_task, content=content, is_file=is_file)
        worker.signals.result.connect(lambda text: self._on_load_text_result(text, language, content if is_file else None))
        worker.signals.finished.connect(self._task_complete)
        worker.signals.error.connect(self._task_error)
        worker.signals.progress.connect(self.update_progress)
        self.threadpool.start(worker)

        self.statusBar().showMessage(self.tr("Cargando y procesando texto..."), 0)

    def _load_text_task(self, content, is_file, progress_callback):
        if is_file:
            file_path = content
            _, extension = os.path.splitext(file_path)
            progress_callback.emit(10, self.tr(f"Extrayendo texto de {extension.upper()}..."))
            if extension.lower() == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            elif extension.lower() == '.docx':
                text = file_io.extract_text_from_docx(file_path)
            elif extension.lower() == '.pdf':
                text = file_io.extract_text_from_pdf(file_path)
            elif extension.lower() == '.rtf':
                text = file_io.extract_text_from_rtf(file_path)
            elif extension.lower() == '.odt':
                text = file_io.extract_text_from_odt(file_path)
            else:
                raise TypeError(self.tr("Tipo de archivo de texto no soportado."))
            progress_callback.emit(100, self.tr("Texto extraído."))
            return text
        else:
            progress_callback.emit(100, self.tr("Contenido directo cargado."))
            return content

    def _on_load_text_result(self, plain_text, language, file_path=None):
        if plain_text is None:
            return # Error already handled by _task_error

        if file_path:
            self.add_to_recent_files(file_path)

        self.set_ui_mode('text')
        self.original_cv_img = None
        self._save_state()
        self.plain_text_content = plain_text
        self.current_language = language
        self.reformat_braille_output()
        for action in [self.action_save, self.action_copy, self.export_menu, self.action_visualize_braille, self.action_print_braille]:
            action.setEnabled(True)
        self.btn_zoom_in_text.setEnabled(True)
        self.btn_zoom_out_text.setEnabled(True)
        self.statusBar().showMessage(self.tr("Texto cargado y procesado."), 3000)

    def update_progress(self, progress, message=""):
        self.statusBar().showMessage(f"{message} {progress}%", 0)

    def _task_error(self, trace):
        exctype, value, tb_str = trace
        logging.error("Ocurrió un error en la tarea en segundo plano:", exc_info=(exctype, value, None))
        QMessageBox.critical(self, self.tr("Error en la Operación"), f"{exctype.__name__}: {value}\n\n{tb_str}")
        self.statusBar().clearMessage()

    def _task_complete(self):
        self.statusBar().clearMessage()

    @gui_error_handler
    def convert_image_to_braille_action(self):
        if self.original_cv_img is None:
            QMessageBox.warning(self, self.tr("Sin imagen"), self.tr("Carga una imagen antes de convertir a Braille."))
            return
        self.update_all_previews()


    @gui_error_handler
    def start_batch_process(self):
        folder_path = QFileDialog.getExistingDirectory(self, self.tr("Seleccionar Carpeta con Imágenes"))
        if not folder_path: return
        items = [self.tr(".txt (Unicode)"), self.tr(".brf (Impresora)")]; item, ok = QInputDialog.getItem(self, self.tr("Seleccionar Formato de Salida"), self.tr("Elige el formato para los archivos:"), items, 0, False)
        if not ok or not item: return
        output_ext = ".brf" if "brf" in item else ".txt"
        settings = {'contrast': self.slider_contrast.value()/100.0, 'brightness': self.slider_brightness.value(), 'invert': self.action_invert.isChecked(), 'dithering': self.action_dithering.isChecked(), 'adaptive_thresholding': self.action_adaptive_thresholding.isChecked()}
        image_files = [f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in self.supported_image_extensions]
        if not image_files: QMessageBox.information(self, self.tr("Carpeta Vacía"), self.tr("La carpeta no contiene imágenes soportadas.")); return

        self.progress_dialog = QProgressDialog(self.tr("Procesando carpeta..."), self.tr("Cancelar"), 0, len(image_files), self)
        self.progress_dialog.setWindowModality(Qt.WindowModal); self.progress_dialog.setWindowTitle(self.tr("Procesamiento por Lotes"))

        self.thread = QThread(); self.worker = BatchWorker(folder_path, settings, output_ext, self.supported_image_extensions); self.worker.moveToThread(self.thread)
        self.progress_dialog.canceled.connect(self.worker.stop); self.thread.started.connect(self.worker.run); self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater); self.worker.finished.connect(self.on_batch_finished); self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self.progress_dialog.setValue); self.thread.start(); self.progress_dialog.exec()

    def on_batch_finished(self, summary):
        self.progress_dialog.setValue(self.progress_dialog.maximum())
        logging.info(f"Procesamiento por lotes finalizado. Resumen: {summary}")
        QMessageBox.information(self, self.tr("Proceso Terminado"), summary)

    @gui_error_handler
    def open_url_dialog(self):
        logging.info("Abriendo diálogo para cargar desde URL.")
        url, ok = QInputDialog.getText(self, self.tr("Cargar desde URL"), self.tr("Introduce la URL:"))
        if ok and url:
            logging.info(f"Iniciando carga desde URL: {url}")
            worker = Worker(self._load_from_url_task, url)
            worker.signals.result.connect(self._on_load_from_url_result)
            worker.signals.finished.connect(self._task_complete)
            worker.signals.error.connect(self._task_error)
            worker.signals.progress.connect(self.update_progress)
            self.threadpool.start(worker)
            self.statusBar().showMessage(self.tr("Cargando contenido de la URL..."), 0)
        else:
            logging.info("El usuario canceló la carga desde URL.")

    def _load_from_url_task(self, url, progress_callback):
        import requests
        from bs4 import BeautifulSoup

        progress_callback.emit(10, self.tr("Conectando con la URL..."))
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        progress_callback.emit(50, self.tr("Procesando HTML..."))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        progress_callback.emit(100, self.tr("Contenido extraído."))
        return "\n".join(line for line in lines if line)

    def _on_load_from_url_result(self, text):
        if text is not None:
            logging.info(f"Contenido de la URL cargado y procesado exitosamente. Longitud del texto: {len(text)}")
            self.load_text(text, is_file=False)


    @gui_error_handler
    def open_google_doc_dialog(self):
        creds = file_io.get_google_credentials()
        if not creds:
            return

        doc_url, ok = QInputDialog.getText(self, self.tr('Abrir Google Doc'), self.tr('Introduce la URL del documento de Google:'))
        if not (ok and doc_url):
            return

        try:
            doc_id = doc_url.split('/d/')[1].split('/')[0]
        except IndexError:
            QMessageBox.critical(self, self.tr("URL Inválida"), self.tr("La URL del Google Doc no es válida."))
            return

        worker = Worker(self._open_google_doc_task, creds, doc_id)
        worker.signals.result.connect(self._on_open_google_doc_result)
        worker.signals.finished.connect(self._task_complete)
        worker.signals.error.connect(self._task_error)
        worker.signals.progress.connect(self.update_progress)
        self.threadpool.start(worker)
        self.statusBar().showMessage(self.tr("Cargando documento de Google..."), 0)

    def _open_google_doc_task(self, creds, doc_id, progress_callback):
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        progress_callback.emit(10, self.tr("Autenticando con Google..."))
        service = build('docs', 'v1', credentials=creds)
        progress_callback.emit(30, self.tr("Obteniendo documento..."))
        doc = service.documents().get(documentId=doc_id).execute()
        content = doc.get('body').get('content')
        progress_callback.emit(70, self.tr("Extrayendo texto del documento..."))
        plain_text = file_io.read_structural_elements(content)
        progress_callback.emit(100, self.tr("Documento cargado."))
        return plain_text

    def _on_open_google_doc_result(self, plain_text):
        if plain_text is not None:
            self.load_text(plain_text, is_file=False)

    def update_image_preview(self):
        if self.original_cv_img is None:
            return

        brightness = self.slider_brightness.value()
        contrast = self.slider_contrast.value() / 100.0
        is_inverted = self.action_invert.isChecked()
        
        # Obtener los parámetros de los sliders del panel
        filter_params = self.filter_settings_panel.get_parameters()

        img_for_braille = None
        display_img_candidate = None

        if self.active_color_filters and self.original_color_cv_img is not None:
            # Apply color filters to the original color image
            filtered_color_img = image_processor.apply_color_filters(self.original_color_cv_img.copy(), self.active_color_filters)
            # Convert filtered color image to grayscale for braille conversion
            img_for_braille = cv2.cvtColor(filtered_color_img, cv2.COLOR_BGR2GRAY)
            display_img_candidate = filtered_color_img
        else:
            # If no specific color filters, use the original grayscale image for braille conversion
            img_for_braille = self.original_cv_img.copy()
            if self.current_color_mode == 'original' and self.original_color_cv_img is not None:
                display_img_candidate = self.original_color_cv_img.copy()
            else:
                display_img_candidate = self.original_cv_img.copy() # Grayscale display

        # Apply noise reduction filter
        if self.current_noise_reduction_filter == 'median':
            img_for_braille = cv2.medianBlur(img_for_braille, filter_params['median_kernel_size'])
        elif self.current_noise_reduction_filter == 'gaussian':
            img_for_braille = cv2.GaussianBlur(img_for_braille, (filter_params['gaussian_kernel_size'], filter_params['gaussian_kernel_size']), 0)
        elif self.current_noise_reduction_filter == 'bilateral':
            img_for_braille = cv2.bilateralFilter(img_for_braille, filter_params['bilateral_d'], filter_params['bilateral_sigma_color'], filter_params['bilateral_sigma_space'])

        # Apply edge detection algorithm
        if self.current_edge_detection_algorithm == 'canny':
            img_for_braille = cv2.Canny(img_for_braille, filter_params['canny_threshold1'], filter_params['canny_threshold2'])
        elif self.current_edge_detection_algorithm == 'sobel':
            sobelx = cv2.Sobel(img_for_braille, cv2.CV_64F, 1, 0, ksize=filter_params['sobel_kernel_size'])
            sobely = cv2.Sobel(img_for_braille, cv2.CV_64F, 0, 1, ksize=filter_params['sobel_kernel_size'])
            img_for_braille = cv2.magnitude(sobelx, sobely).astype(np.uint8)
        elif self.current_edge_detection_algorithm == 'prewitt':
            kernelx = np.array([[1,0,-1],[1,0,-1],[1,0,-1]])
            kernely = np.array([[1,1,1],[0,0,0],[-1,-1,-1]])
            img_prewittx = cv2.filter2D(img_for_braille, cv2.CV_64F, kernelx)
            img_prewitty = cv2.filter2D(img_for_braille, cv2.CV_64F, kernely)
            img_for_braille = cv2.magnitude(img_prewittx, img_prewitty).astype(np.uint8)
        elif self.current_edge_detection_algorithm == 'laplacian':
            img_for_braille = cv2.Laplacian(img_for_braille.astype(np.float64), cv2.CV_64F, ksize=filter_params['laplacian_kernel_size']).astype(np.uint8)

        # Apply invert, brightness, contrast to the image for braille conversion
        if is_inverted: 
            img_for_braille = cv2.bitwise_not(img_for_braille)
        adjusted_cv_img = cv2.convertScaleAbs(img_for_braille, alpha=contrast, beta=brightness)

        # Apply invert, brightness, contrast to the image for display
        if display_img_candidate is not None:
            if is_inverted:
                display_img_candidate = cv2.bitwise_not(display_img_candidate)
            display_img = cv2.convertScaleAbs(display_img_candidate, alpha=contrast, beta=brightness)
        else:
            display_img = adjusted_cv_img # Fallback to braille processed image for display
            
        if display_img.ndim == 3: # Color image
            h, w, ch = display_img.shape
            bytes_per_line = ch * w
            qt_image = QImage(display_img.data, w, h, bytes_per_line, QImage.Format_BGR888)
        else: # Grayscale image
            h, w = display_img.shape
            qt_image = QImage(display_img.data, w, h, w, QImage.Format_Grayscale8)

        base_pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = base_pixmap.scaled(base_pixmap.size() * self.zoom_factor, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_image_preview.setPixmap(scaled_pixmap)

    @gui_error_handler
    def update_all_previews(self):
        self.update_image_preview()
        self.update_braille_output()

    def update_braille_output(self):
        if self.original_cv_img is None: return
        logging.info("Iniciando actualización de braille.")
        brightness = self.slider_brightness.value()
        contrast = self.slider_contrast.value() / 100.0
        is_inverted = self.action_invert.isChecked()
        use_dithering = self.action_dithering.isChecked()
        lines_mode = self.action_lines.isChecked()
        use_adaptive_thresholding = self.action_adaptive_thresholding.isChecked()

        # Obtener los parámetros de los sliders del panel
        filter_params = self.filter_settings_panel.get_parameters()

        worker = Worker(self._update_previews_task, self.original_cv_img, self.original_color_cv_img, self.image_path, brightness, contrast, is_inverted, use_dithering, lines_mode, self.braille_dots_mode, use_adaptive_thresholding, self.current_color_mode, self.active_color_filters, self.current_noise_reduction_filter, self.current_edge_detection_algorithm, filter_params)
        worker.signals.result.connect(self._on_update_previews_result)
        worker.signals.finished.connect(self._task_complete)
        worker.signals.error.connect(self._task_error)
        worker.signals.progress.connect(self.update_progress)
        self.threadpool.start(worker)
        self.statusBar().showMessage(self.tr("Procesando imagen..."), 0)

    def _update_previews_task(self, original_img, original_color_img, image_path, brightness, contrast, is_inverted, use_dithering, lines_mode, dots_mode, use_adaptive_thresholding, current_color_mode, active_color_filters, current_noise_reduction_filter, current_edge_detection_algorithm, filter_params, progress_callback):
        progress_callback.emit(10, self.tr("Ajustando imagen..."))
        
        # Aplicar el recorte (ROI) si existe
        if self.crop_roi:
            x, y, w, h = self.crop_roi
            original_img = original_img[y:y+h, x:x+w]
            if original_color_img is not None:
                original_color_img = original_color_img[y:y+h, x:x+w]

        img_for_braille = None
        display_img_candidate = None

        if active_color_filters and original_color_img is not None:
            # Apply color filters to the original color image
            filtered_color_img = image_processor.apply_color_filters(original_color_img.copy(), active_color_filters)
            # Convert filtered color image to grayscale for braille conversion
            img_for_braille = cv2.cvtColor(filtered_color_img, cv2.COLOR_BGR2GRAY)
            display_img_candidate = filtered_color_img
        else:
            # If no specific color filters, use the original grayscale image for braille conversion
            img_for_braille = original_img.copy()
            if current_color_mode == 'original' and original_color_img is not None:
                display_img_candidate = original_color_img.copy()
            else:
                display_img_candidate = original_img.copy() # Grayscale display

        # Apply noise reduction filter
        if current_noise_reduction_filter == 'median':
            img_for_braille = cv2.medianBlur(img_for_braille, filter_params['median_kernel_size'])
        elif current_noise_reduction_filter == 'gaussian':
            img_for_braille = cv2.GaussianBlur(img_for_braille, (filter_params['gaussian_kernel_size'], filter_params['gaussian_kernel_size']), 0)
        elif current_noise_reduction_filter == 'bilateral':
            img_for_braille = cv2.bilateralFilter(img_for_braille, filter_params['bilateral_d'], filter_params['bilateral_sigma_color'], filter_params['bilateral_sigma_space'])

        # Apply edge detection algorithm
        if current_edge_detection_algorithm == 'canny':
            img_for_braille = cv2.Canny(img_for_braille, filter_params['canny_threshold1'], filter_params['canny_threshold2'])
        elif current_edge_detection_algorithm == 'sobel':
            sobelx = cv2.Sobel(img_for_braille, cv2.CV_64F, 1, 0, ksize=filter_params['sobel_kernel_size'])
            sobely = cv2.Sobel(img_for_braille, cv2.CV_64F, 0, 1, ksize=filter_params['sobel_kernel_size'])
            img_for_braille = cv2.magnitude(sobelx, sobely).astype(np.uint8)
        elif current_edge_detection_algorithm == 'prewitt':
            kernelx = np.array([[1,0,-1],[1,0,-1],[1,0,-1]])
            kernely = np.array([[1,1,1],[0,0,0],[-1,-1,-1]])
            img_prewittx = cv2.filter2D(img_for_braille, cv2.CV_64F, kernelx)
            img_prewitty = cv2.filter2D(img_for_braille, cv2.CV_64F, kernely)
            img_for_braille = cv2.magnitude(img_prewittx, img_prewitty).astype(np.uint8)
        elif current_edge_detection_algorithm == 'laplacian':
            img_for_braille = cv2.Laplacian(img_for_braille.astype(np.float64), cv2.CV_64F, ksize=filter_params['laplacian_kernel_size']).astype(np.uint8)

        # Apply invert, brightness, contrast to the image for braille conversion
        if is_inverted: 
            img_for_braille = cv2.bitwise_not(img_for_braille)
        adjusted_cv_img = cv2.convertScaleAbs(img_for_braille, alpha=contrast, beta=brightness)

        progress_callback.emit(50, self.tr("Convirtiendo a Braille..."))
        
        raw_braille_text = image_processor.convert_image_to_braille(adjusted_cv_img, 100, contrast, brightness, is_inverted, use_dithering, dots_mode, use_adaptive_thresholding)
        progress_callback.emit(100, self.tr("Procesamiento completado."))

        return adjusted_cv_img, raw_braille_text

    def _on_update_previews_result(self, result):
        adjusted_cv_img, raw_braille_text = result
        logging.info("Previsualizaciones actualizadas exitosamente.")
        
        self.raw_braille_text = raw_braille_text
        self.reformat_braille_output()
        self._save_state()
        self.statusBar().showMessage(self.tr("Imagen procesada."), 3000)

        # Save image adjustment settings
        settings = QSettings("BrailleApp", "BrailleConverter")
        settings.setValue("brightness", self.slider_brightness.value())
        settings.setValue("contrast", self.slider_contrast.value())
        settings.setValue("invert", self.action_invert.isChecked())
        settings.setValue("dithering", self.action_dithering.isChecked())
        settings.setValue("lines", self.action_lines.isChecked())
        settings.setValue("adaptive_thresholding", self.action_adaptive_thresholding.isChecked())
        settings.setValue("remove_noise", self.action_remove_noise.isChecked())

    def _toggle_crop_mode(self, checked):
        """Activa o desactiva el modo de recorte en el ImageLabel."""
        logging.debug(f"Modo de recorte cambiado a: {checked}")
        self.lbl_image_preview.set_crop_active(checked)
        if not checked:
            # Si el usuario desactiva el modo, se limpia la selección
            self.lbl_image_preview.clear_selection()

    def _on_crop_selection_cleared(self):
        """Slot para cuando la selección de recorte es limpiada desde el ImageLabel."""
        self.crop_roi = None
        self.update_all_previews()

    def _on_new_crop_selection(self, selection_rect):
        """Slot que se activa cuando se dibuja un nuevo rectángulo de recorte."""
        if self.original_cv_img is None or not self.lbl_image_preview.pixmap():
            return

        # Convertir las coordenadas del QRect del widget a las coordenadas de la imagen original
        label_size = self.lbl_image_preview.size()
        pixmap = self.lbl_image_preview.pixmap()
        
        # Calcular el tamaño y la posición real del pixmap dentro del QLabel (considerando el escalado)
        pixmap_size = pixmap.size()
        scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        x_offset = (label_size.width() - scaled_pixmap.width()) / 2
        y_offset = (label_size.height() - scaled_pixmap.height()) / 2

        # Escala real aplicada a la imagen
        x_scale = scaled_pixmap.width() / self.original_cv_img.shape[1]
        y_scale = scaled_pixmap.height() / self.original_cv_img.shape[0]

        if x_scale == 0 or y_scale == 0:
            return

        # Mapear las coordenadas del rectángulo de selección a la imagen original
        img_x = int((selection_rect.x() - x_offset) / x_scale)
        img_y = int((selection_rect.y() - y_offset) / y_scale)
        img_w = int(selection_rect.width() / x_scale)
        img_h = int(selection_rect.height() / y_scale)

        # Asegurarse de que las coordenadas estén dentro de los límites de la imagen
        img_x = max(0, img_x)
        img_y = max(0, img_y)
        img_w = min(img_w, self.original_cv_img.shape[1] - img_x)
        img_h = min(img_h, self.original_cv_img.shape[0] - img_y)

        self.crop_roi = (img_x, img_y, img_w, img_h)
        logging.info(f"Nueva región de recorte (ROI) establecida: {self.crop_roi}")

        # Desactivar el modo recorte para evitar redibujar accidentalmente
        self.action_crop.setChecked(False)
        self.lbl_image_preview.set_crop_active(False)

        # Actualizar las previsualizaciones con la nueva ROI
        self.update_all_previews()

    def _toggle_drawing_mode(self, checked):
        if checked:
            if not self.raw_braille_text:
                QMessageBox.warning(self, self.tr("Sin Contenido Braille"), self.tr("Primero convierte una imagen o texto a Braille para poder editarlo."))
                self.action_drawing_mode.setChecked(False)
                return
            
            self.braille_canvas.set_braille_string(self.raw_braille_text)
            self.drawing_toolbar.setVisible(True)
            self.view_stack.setCurrentWidget(self.drawing_view_widget)
        else:
            self.raw_braille_text = self.braille_canvas.get_braille_string()
            self.reformat_braille_output() # Actualiza el QTextEdit
            self.drawing_toolbar.setVisible(False)
            self.view_stack.setCurrentWidget(self.normal_view_widget)

    def set_drawing_tool(self, tool):
        self.braille_canvas.set_tool(tool)

    def _on_canvas_changed(self):
        # Este método se puede usar para habilitar un botón de "Guardar" o similar
        # en el futuro, para indicar que hay cambios sin guardar en el lienzo.
        pass



    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls() and len(mime_data.urls()) == 1:
            url = mime_data.urls()[0]
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if os.path.splitext(file_path)[1].lower() in self.supported_image_extensions:
                    logging.debug(f"Aceptando arrastre de archivo: {file_path}")
                    event.acceptProposedAction()

    def dropEvent(self, event): 
        file_path = event.mimeData().urls()[0].toLocalFile()
        logging.info(f"Archivo soltado: {file_path}")
        self.load_image(file_path)

    def toggle_adjustments_widget(self): 
        self.adjustments_widget.setVisible(not self.adjustments_widget.isVisible())
        self.action_adjust.setChecked(self.adjustments_widget.isVisible())
        logging.info(f"Visibilidad del widget de ajustes cambiada a: {self.adjustments_widget.isVisible()}")

    @gui_error_handler
    def remove_noise(self):
        if self.original_cv_img is None: return
        logging.info("Iniciando eliminación de ruido.")
        self.statusBar().showMessage(self.tr("Quitando ruido..."), 0)
        
        denoised_img = cv2.fastNlMeansDenoising(self.original_cv_img, None, 30, 7, 21)
        
        self.original_cv_img = denoised_img
        self.update_all_previews()
        self._save_state()
        logging.info("Eliminación de ruido completada.")
        self.statusBar().showMessage(self.tr("Ruido quitado."), 3000)

    def fit_to_window(self):
        if self.original_cv_img is None: return
        viewport_size = self.scroll_area_img.viewport().size()
        h, w = self.original_cv_img.shape
        if w == 0 or h == 0: return
        self.zoom_factor = min(viewport_size.width() / w, viewport_size.height() / h) * 0.5
        self.update_all_previews()

    def zoom_in(self):
        if self.original_cv_img is None: return
        self.zoom_factor *= 1.25
        logging.debug(f"Zoom in: {self.zoom_factor}")
        self.update_all_previews()

    def zoom_out(self):
        if self.original_cv_img is None: return
        self.zoom_factor /= 1.25
        logging.debug(f"Zoom out: {self.zoom_factor}")
        self.update_all_previews()

    def zoom_in_text(self):
        self.braille_display.zoomIn()
        if self.latin_display.isVisible():
            self.latin_display.zoomIn()

    def zoom_out_text(self):
        self.braille_display.zoomOut()
        if self.latin_display.isVisible():
            self.latin_display.zoomOut()

    def zoom_in_latin(self):
        self.latin_display.zoomIn()

    def zoom_out_latin(self):
        self.latin_display.zoomOut()

    def resizeEvent(self, event):
        if self.original_cv_img is not None: self.fit_to_window()
        super().resizeEvent(event)

    @gui_error_handler
    def save_result_dialog(self):
        logging.info("Abriendo diálogo para guardar resultado.")
        braille_text = self.braille_display.toPlainText()
        latin_text = self.latin_display.toPlainText()

        if not (braille_text or latin_text):
            QMessageBox.warning(self, self.tr("Nada que guardar"), self.tr("No hay resultado válido."))
            logging.warning("Intento de guardar sin contenido válido.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Guardar como Texto"), "resultado.txt", self.tr("Archivos de Texto (*.txt)"))
        if file_path:
            logging.info(f"Guardando resultado en: {file_path}")
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    if self.latin_display.isVisible():
                        f.write(self.tr("--- Texto en Braille ---\n"))
                        f.write(braille_text)
                        f.write(self.tr("\n\n--- Texto en Tinta ---\n"))
                        f.write(latin_text)
                    else:
                        f.write(braille_text)
                self.statusBar().showMessage(self.tr(f"Archivo .txt guardado en {file_path}"), 3000)
                logging.info(f"Archivo guardado exitosamente: {file_path}")
            except IOError as e:
                QMessageBox.critical(self, self.tr("Error al Guardar"), self.tr(f"No se pudo escribir en el archivo: {file_path}\n{e}"))
                logging.error(f"Error de E/S al guardar el archivo {file_path}", exc_info=True)
            except Exception as e:
                QMessageBox.critical(self, self.tr("Error Inesperado"), str(e))
                logging.error(f"Error inesperado al guardar el archivo {file_path}", exc_info=True)
        else:
            logging.info("El usuario canceló el guardado del archivo.")

    @gui_error_handler
    def export_as_brf(self):
        braille_text = self.braille_display.toPlainText()
        if not braille_text or braille_text.startswith("Error:"): 
            QMessageBox.warning(self, self.tr("Nada que exportar"), self.tr("No hay resultado válido."))
            logging.warning("Intento de exportar a BRF sin contenido válido.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Exportar como BRF"), "resultado.brf", self.tr("Archivos Braille Ready Format (*.brf)"))
        if file_path:
            logging.info(f"Exportando a BRF en: {file_path}")
            try:
                brf_string = braille_processor.convert_unicode_to_brf_string(braille_text, self.current_language, self.braille_dots_mode)
                with open(file_path, 'w', encoding='ascii') as f: 
                    f.write(brf_string)
                self.statusBar().showMessage(self.tr(f"Archivo .brf exportado en {file_path}"), 3000)
                logging.info(f"Archivo BRF exportado exitosamente: {file_path}")
            except IOError as e:
                QMessageBox.critical(self, self.tr("Error al Exportar"), self.tr(f"No se pudo escribir en el archivo: {file_path}\n{e}"))
                logging.error(f"Error de E/S al exportar a BRF {file_path}", exc_info=True)
            except Exception as e:
                QMessageBox.critical(self, self.tr("Error de Conversión"), self.tr(f"No se pudo convertir a formato BRF.\n{e}"))
                logging.error(f"Error de conversión al exportar a BRF {file_path}", exc_info=True)
        else:
            logging.info("El usuario canceló la exportación a BRF.")

    @gui_error_handler
    def export_as_bra(self):
        braille_text = self.braille_display.toPlainText()
        if not braille_text or braille_text.startswith("Error:"): 
            QMessageBox.warning(self, self.tr("Nada que exportar"), self.tr("No hay resultado válido."))
            logging.warning("Intento de exportar a BRA sin contenido válido.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Exportar como BRA"), "resultado.bra", self.tr("Archivos Braille (*.bra)"))
        if file_path:
            logging.info(f"Exportando a BRA en: {file_path}")
            try:
                with open(file_path, 'w', encoding='utf-8') as f: 
                    f.write(braille_text)
                self.statusBar().showMessage(self.tr(f"Archivo .bra exportado en {file_path}"), 3000)
                logging.info(f"Archivo BRA exportado exitosamente: {file_path}")
            except IOError as e:
                QMessageBox.critical(self, self.tr("Error al Exportar"), self.tr(f"No se pudo escribir en el archivo: {file_path}\n{e}"))
                logging.error(f"Error de E/S al exportar a BRA {file_path}", exc_info=True)
            except Exception as e:
                QMessageBox.critical(self, self.tr("Error Inesperado"), str(e))
                logging.error(f"Error inesperado al exportar a BRA {file_path}", exc_info=True)
        else:
            logging.info("El usuario canceló la exportación a BRA.")

    def show_shortcuts_dialog(self):
        logging.info("Mostrando diálogo de atajos de teclado.")
        QMessageBox.information(self, self.tr("Atajos de Teclado"), self.tr("""<h3>Atajos de Teclado</h3>
            <p>Usa las siguientes combinaciones de teclas para controlar la aplicación:</p>
            <ul>
                <li><b>Ctrl+O:</b> Cargar nueva imagen</li>
                <li><b>Ctrl+T:</b> Cargar un archivo de texto</li>
                <li><b>Ctrl+M:</b> Abrir la ventana de función polinómica</li>
                <li><b>Ctrl+Shift+C:</b> Abrir la ventana de función compuesta</li>
                <li><b>Ctrl+Shift+O:</b> Procesar una carpeta de imágenes</li>
                <li><b>Ctrl+S:</b> Guardar el resultado Braille como .txt</li>
                <li><b>Ctrl+C:</b> Copiar el texto Braille al portapapeles</li>
                <li><b>Ctrl++:</b> Aumentar zoom de la imagen</li>
                <li><b>Ctrl+-:</b> Reducir zoom de la imagen</li>
            </ul>"""))

    def open_linear_function_dialog(self):
        dialog = LinearFunctionDialog(self)
        if dialog.exec():
            slope, intercept = dialog.get_values()
            try:
                slope_val = float(slope) if slope.strip() else 0
                intercept_val = float(intercept) if intercept.strip() else 0

                self.progress_dialog = QProgressDialog(self.tr("Generando gráfico..."), self.tr("Cancelar"), 0, 0, self)
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                self.progress_dialog.setWindowTitle(self.tr("Procesando..."))
                self.progress_dialog.show()

                worker = Worker(self._generate_linear_graph_task, slope_val, intercept_val)
                worker.signals.result.connect(self._on_linear_graph_generated)
                worker.signals.finished.connect(self.progress_dialog.close)
                self.threadpool.start(worker)

            except ValueError:
                QMessageBox.critical(self, "Error de Entrada", "La pendiente y el corte deben ser números.")

    def _generate_linear_graph_task(self, slope, intercept, progress_callback):
        # This task now only returns the parameters, not a widget
        return {"type": "linear", "slope": slope, "intercept": intercept}

    def _on_linear_graph_generated(self, function_data):
        if function_data:
            slope = function_data['slope']
            intercept = function_data['intercept']
            graph_widget = LinearGraphWidget(slope, intercept, self.show_equation, self.show_roots, self)
            
            self.graph_tabs.setVisible(True)
            self.graph_tabs.addTab(graph_widget, self.tr("Lineal"))
            self.graph_tabs.setCurrentWidget(graph_widget)
            self.current_function_data = function_data

    def open_quadratic_function_dialog(self):
        dialog = QuadraticFunctionDialog(self)
        if dialog.exec():
            a, b, c = dialog.get_values()
            try:
                a_val = float(a) if a.strip() else 0
                b_val = float(b) if b.strip() else 0
                c_val = float(c) if c.strip() else 0

                if a_val == 0:
                    QMessageBox.warning(self, "Entrada Inválida", "El coeficiente cuadrático (a) no puede ser cero para una función cuadrática.")
                    return

                self.progress_dialog = QProgressDialog(self.tr("Generando gráfico..."), self.tr("Cancelar"), 0, 0, self)
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                self.progress_dialog.setWindowTitle(self.tr("Procesando..."))
                self.progress_dialog.show()

                worker = Worker(self._generate_quadratic_graph_task, a_val, b_val, c_val)
                worker.signals.result.connect(self._on_quadratic_graph_generated)
                worker.signals.finished.connect(self.progress_dialog.close)
                self.threadpool.start(worker)

            except ValueError:
                QMessageBox.critical(self, "Error de Entrada", "Los coeficientes deben ser números.")

    def _generate_quadratic_graph_task(self, a, b, c, progress_callback):
        return {"type": "quadratic", "a": a, "b": b, "c": c}

    def _on_quadratic_graph_generated(self, function_data):
        if function_data:
            a = function_data['a']
            b = function_data['b']
            c = function_data['c']
            graph_widget = QuadraticGraphWidget(a, b, c, self.show_equation, self.show_roots, self)

            self.graph_tabs.setVisible(True)
            self.graph_tabs.addTab(graph_widget, self.tr("Cuadrática"))
            self.graph_tabs.setCurrentWidget(graph_widget)
            self.current_function_data = function_data

    def open_cubic_function_dialog(self):
        dialog = CubicFunctionDialog(self)
        if dialog.exec():
            a, b, c, d = dialog.get_values()
            try:
                a_val = float(a) if a.strip() else 0
                b_val = float(b) if b.strip() else 0
                c_val = float(c) if c.strip() else 0
                d_val = float(d) if d.strip() else 0

                if a_val == 0:
                    QMessageBox.warning(self, "Entrada Inválida", "El coeficiente cúbico (a) no puede ser cero para una función cúbica.")
                    return

                self.progress_dialog = QProgressDialog(self.tr("Generando gráfico..."), self.tr("Cancelar"), 0, 0, self)
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                self.progress_dialog.setWindowTitle(self.tr("Procesando..."))
                self.progress_dialog.show()

                worker = Worker(self._generate_cubic_graph_task, a_val, b_val, c_val, d_val)
                worker.signals.result.connect(self._on_cubic_graph_generated)
                worker.signals.finished.connect(self.progress_dialog.close)
                self.threadpool.start(worker)

            except ValueError:
                QMessageBox.critical(self, "Error de Entrada", "Los coeficientes deben ser números.")

    def _generate_cubic_graph_task(self, a, b, c, d, progress_callback):
        return {"type": "cubic", "a": a, "b": b, "c": c, "d": d}

    def _on_cubic_graph_generated(self, function_data):
        if function_data:
            a = function_data['a']
            b = function_data['b']
            c = function_data['c']
            d = function_data['d']
            graph_widget = CubicGraphWidget(a, b, c, d, self.show_equation, self.show_roots, self)

            self.graph_tabs.setVisible(True)
            self.graph_tabs.addTab(graph_widget, self.tr("Cúbica"))
            self.graph_tabs.setCurrentWidget(graph_widget)
            self.current_function_data = function_data

    def open_polynomial_function_dialog(self):
        dialog = PolynomialFunctionDialog(self)
        if dialog.exec():
            coeffs_str = dialog.get_values()
            try:
                coeffs = [float(c.strip()) for c in coeffs_str.split(',') if c.strip()]
                if not coeffs:
                    QMessageBox.critical(self, "Error de Entrada", "Debe introducir al menos un coeficiente.")
                    return

                self.progress_dialog = QProgressDialog(self.tr("Generando gráfico..."), self.tr("Cancelar"), 0, 0, self)
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                self.progress_dialog.setWindowTitle(self.tr("Procesando..."))
                self.progress_dialog.show()

                worker = Worker(self._generate_polynomial_graph_task, coeffs)
                worker.signals.result.connect(self._on_polynomial_graph_generated)
                worker.signals.finished.connect(self.progress_dialog.close)
                self.threadpool.start(worker)

            except ValueError:
                QMessageBox.critical(self, "Error de Entrada", "Los coeficientes deben ser números separados por comas.")

    def _generate_polynomial_graph_task(self, coeffs, progress_callback):
        return {"type": "polynomial", "coeffs": coeffs}

    def _on_polynomial_graph_generated(self, function_data):
        if function_data:
            coeffs = function_data['coeffs']
            graph_widget = PolynomialGraphWidget(coeffs, self.show_equation, self.show_roots, self)

            self.graph_tabs.setVisible(True)
            self.graph_tabs.addTab(graph_widget, self.tr("Polinómica"))
            self.graph_tabs.setCurrentWidget(graph_widget)
            self.current_function_data = function_data

    def open_points_graph_dialog(self):
        dialog = PointsDialog(self)
        if dialog.exec():
            points = dialog.get_points()
            if points:
                self.progress_dialog = QProgressDialog(self.tr("Generando gráfico..."), self.tr("Cancelar"), 0, 0, self)
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                self.progress_dialog.setWindowTitle(self.tr("Procesando..."))
                self.progress_dialog.show()

                worker = Worker(self._generate_points_graph_task, points)
                worker.signals.result.connect(self._on_points_graph_generated)
                worker.signals.finished.connect(self.progress_dialog.close)
                self.threadpool.start(worker)

    def _generate_points_graph_task(self, points, progress_callback):
        return {"type": "points", "points": points}

    def _on_points_graph_generated(self, function_data):
        if function_data:
            points = function_data['points']
            graph_widget = PointsGraphWidget(points, self)

            self.graph_tabs.setVisible(True)
            self.graph_tabs.addTab(graph_widget, self.tr("Puntos"))
            self.graph_tabs.setCurrentWidget(graph_widget)
            self.current_function_data = function_data







    def open_composite_function_dialog_un_interval(self):
        dialog = CompositeFunctionDialog(self)
        if dialog.exec():
            function_domain_pairs = dialog.get_parsed_data()
            if not function_domain_pairs:
                return
            
            if len(function_domain_pairs) > 1:
                QMessageBox.information(self, self.tr("Múltiples Intervalos"), 
                                             self.tr("Ha introducido más de un intervalo. Por favor, use las opciones 'Dos intervalos' o 'Tres intervalos' para esta funcionalidad."))
                return

            self.progress_dialog = QProgressDialog(self.tr("Generando gráfico..."), self.tr("Cancelar"), 0, 0, self)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setWindowTitle(self.tr("Procesando..."))
            self.progress_dialog.show()

            worker = Worker(self._generate_composite_graph_task, function_domain_pairs)
            worker.signals.result.connect(self._on_composite_graph_generated)
            worker.signals.finished.connect(self.progress_dialog.close)
            self.threadpool.start(worker)

    def _generate_composite_graph_task(self, function_domain_pairs, progress_callback):
        return {"type": "composite", "functions": function_domain_pairs}

    def _on_composite_graph_generated(self, function_data):
        if function_data:
            function_domain_pairs = function_data['functions']
            graph_widget = CompositeGraphWidget(function_domain_pairs, self)

            self.graph_tabs.setVisible(True)
            self.graph_tabs.addTab(graph_widget, self.tr("Compuesta"))
            self.graph_tabs.setCurrentWidget(graph_widget)
            self.current_function_data = function_data

    def open_composite_function_dialog_dos_intervalos(self):
        dialog = ThreeIntervalFunctionDialog(self)
        if dialog.exec():
            function_domain_pairs = dialog.get_parsed_data()
            if not function_domain_pairs:
                return
            
            if len(function_domain_pairs) != 3:
                QMessageBox.warning(self, self.tr("Entrada Inválida"), self.tr("Para 'Dos intervalos', por favor, introduce exactamente tres funciones (x=a, a<x<b, x=b)."))
                return

            self.progress_dialog = QProgressDialog(self.tr("Generando gráfico..."), self.tr("Cancelar"), 0, 0, self)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setWindowTitle(self.tr("Procesando..."))
            self.progress_dialog.show()

            worker = Worker(self._generate_composite_graph_task, function_domain_pairs)
            worker.signals.result.connect(self._on_composite_graph_generated)
            worker.signals.finished.connect(self.progress_dialog.close)
            self.threadpool.start(worker)

    def open_composite_function_dialog(self):
        dialog = CompositeFunctionDialog(self)
        if dialog.exec():
            function_domain_pairs = dialog.get_parsed_data()
            if not function_domain_pairs:
                return
            


            self.progress_dialog = QProgressDialog(self.tr("Generando gráfico..."), self.tr("Cancelar"), 0, 0, self)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setWindowTitle(self.tr("Procesando..."))
            self.progress_dialog.show()

            worker = Worker(self._generate_composite_graph_task, function_domain_pairs)
            worker.signals.result.connect(self._on_composite_graph_generated)
            worker.signals.finished.connect(self.progress_dialog.close)
            self.threadpool.start(worker)

    def open_function_analysis_dialog(self):
        if self.current_function_data is None:
            QMessageBox.warning(self, self.tr("No hay función para analizar"), self.tr("Primero genera un gráfico de función para poder analizarlo."))
            return

        analysis_result, braille_analysis = function_analyzer.get_function_analysis(self.current_function_data, self.current_language, self.braille_dots_mode)
        
        dialog = FunctionAnalysisDialog(analysis_result, braille_analysis, self)
        dialog.exec()



    def toggle_show_equation(self, checked):
        self.show_equation = checked
        settings = QSettings("BrailleApp", "BrailleConverter")
        settings.setValue("show_equation", checked)
        # Re-open graph dialog if open, or update if possible

    def toggle_show_roots(self, checked):
        self.show_roots = checked
        settings = QSettings("BrailleApp", "BrailleConverter")
        settings.setValue("show_roots", checked)
        # Re-open graph dialog if open, or update if possible

    def copy_braille_to_clipboard(self):
        clipboard = QApplication.clipboard()
        text_to_copy = self.latin_display.toPlainText() if self.latin_display.isVisible() else self.braille_display.toPlainText()
        
        if text_to_copy:
            clipboard.setText(text_to_copy)
            self.statusBar().showMessage(self.tr("Texto copiado al portapapeles"), 2000)
            logging.info("Texto copiado al portapapeles.")
        else:
            logging.warning("Intento de copiar al portapapeles sin texto.")

    @gui_error_handler
    def save_image_settings(self):
        if self.original_cv_img is None:
            QMessageBox.warning(self, self.tr("Sin imagen"), self.tr("No hay una imagen cargada para guardar sus ajustes."))
            return

        file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Guardar Ajustes de Imagen"), "", self.tr("Archivos de Ajustes (*.json)"))
        if not file_path:
            return

        settings = {
            'brightness': self.slider_brightness.value(),
            'contrast': self.slider_contrast.value(),
            'inverted': self.action_invert.isChecked(),
            'dithering': self.action_dithering.isChecked(),
            'lines': self.action_lines.isChecked(),
            'adaptive_thresholding': self.action_adaptive_thresholding.isChecked(),
        }

        # Obtener los parámetros del panel de filtros y añadirlos a la configuración
        filter_params = self.filter_settings_panel.get_parameters()
        settings.update(filter_params)

        try:
            with open(file_path, 'w') as f:
                json.dump(settings, f, indent=4)
            self.statusBar().showMessage(self.tr("Ajustes de imagen guardados."), 3000)
            logging.info(f"Ajustes de imagen guardados en: {file_path}")
        except IOError as e:
            QMessageBox.critical(self, self.tr("Error al Guardar"), self.tr(f"No se pudo escribir en el archivo: {file_path}\n{e}"))
            logging.error(f"Error de E/S al guardar los ajustes de imagen en {file_path}", exc_info=True)

    @gui_error_handler
    def load_image_settings(self):
        if self.original_cv_img is None:
            QMessageBox.warning(self, self.tr("Sin imagen"), self.tr("Carga una imagen antes de cargar ajustes."))
            return

        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Cargar Ajustes de Imagen"), "", self.tr("Archivos de Ajustes (*.json)"))
        if not file_path:
            return

        try:
            with open(file_path, 'r') as f:
                settings = json.load(f)

            self.action_adaptive_thresholding.triggered.disconnect()
            self.action_remove_noise.triggered.disconnect()
            self.action_color_original.triggered.disconnect()
            self.action_color_grayscale.triggered.disconnect()
            self.action_color_red.triggered.disconnect()
            self.action_color_green.triggered.disconnect()
            self.action_color_blue.triggered.disconnect()
            self.action_noise_none.triggered.disconnect()
            self.action_noise_median.triggered.disconnect()
            self.action_noise_gaussian.triggered.disconnect()
            self.action_noise_bilateral.triggered.disconnect()
            self.action_edge_none.triggered.disconnect()
            self.action_edge_canny.triggered.disconnect()
            self.action_edge_sobel.triggered.disconnect()
            self.action_edge_prewitt.triggered.disconnect()
            self.action_edge_laplacian.triggered.disconnect()

            # Cargar los parámetros de los filtros en el panel
            self.filter_settings_panel.set_parameters(settings)

            self.slider_brightness.setValue(settings.get('brightness', 0))
            self.slider_contrast.setValue(settings.get('contrast', 100))
            self.action_invert.setChecked(settings.get('inverted', False))
            self.action_dithering.setChecked(settings.get('dithering', False))
            self.action_lines.setChecked(settings.get('lines', False))
            self.action_adaptive_thresholding.setChecked(settings.get('adaptive_thresholding', False))
            self.action_remove_noise.setChecked(settings.get('remove_noise', False))
            self.current_color_mode = settings.get('current_color_mode', 'original')

            self.current_segmentation_algorithm = settings.get("segmentation_algorithm", 'none')
            segmentation_rect_str = settings.get("segmentation_rect", None)
            if segmentation_rect_str:
                self.segmentation_rect = tuple(map(int, segmentation_rect_str.split(',')))
            else:
                self.segmentation_rect = None

            # Reconnect signals
            self.slider_brightness.valueChanged.connect(self.update_all_previews)
            self.slider_contrast.valueChanged.connect(self.update_all_previews)
            self.action_invert.triggered.connect(lambda: self.update_all_previews())
            self.action_dithering.triggered.connect(lambda: self.update_all_previews())
            self.action_lines.triggered.connect(lambda: self.update_all_previews())
            self.action_adaptive_thresholding.triggered.connect(lambda: self.update_all_previews())
            self.action_remove_noise.triggered.connect(self.remove_noise)
            self.action_color_original.triggered.connect(lambda: self.set_color_mode('original'))
            self.action_color_grayscale.triggered.connect(lambda: self.set_color_mode('grayscale'))
            self.action_color_red.triggered.connect(lambda: self.toggle_color_filter('red', self.action_color_red.isChecked()))
            self.action_color_green.triggered.connect(lambda: self.toggle_color_filter('green', self.action_color_green.isChecked()))
            self.action_color_blue.triggered.connect(lambda: self.toggle_color_filter('blue', self.action_color_blue.isChecked()))
            self.action_noise_none.triggered.connect(lambda: self.set_noise_reduction_filter('none'))
            self.action_noise_median.triggered.connect(lambda: self.set_noise_reduction_filter('median'))
            self.action_noise_gaussian.triggered.connect(lambda: self.set_noise_reduction_filter('gaussian'))
            self.action_noise_bilateral.triggered.connect(lambda: self.set_noise_reduction_filter('bilateral'))
            self.action_edge_none.triggered.connect(lambda: self.set_edge_detection_algorithm('none'))
            self.action_edge_canny.triggered.connect(lambda: self.set_edge_detection_algorithm('canny'))
            self.action_edge_sobel.triggered.connect(lambda: self.set_edge_detection_algorithm('sobel'))
            self.action_edge_prewitt.triggered.connect(lambda: self.set_edge_detection_algorithm('prewitt'))
            self.action_edge_laplacian.triggered.connect(lambda: self.set_edge_detection_algorithm('laplacian'))

            # Reconnect signals for segmentation
            self.action_segmentation_none.triggered.connect(lambda: self.set_segmentation_algorithm('none'))
            self.action_segmentation_grabcut.triggered.connect(lambda: self.set_segmentation_algorithm('grabcut'))

            self.statusBar().showMessage(self.tr("Ajustes de imagen cargados."), 3000)
            logging.info(f"Ajustes de imagen cargados desde: {file_path}")

            self.update_all_previews()
            self._save_state()

        except (IOError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, self.tr("Error al Cargar"), self.tr(f"No se pudo leer o procesar el archivo: {file_path}\n{e}"))
            logging.error(f"Error al cargar los ajustes de imagen desde {file_path}", exc_info=True)
        except KeyError as e:
            QMessageBox.critical(self, self.tr("Error de Formato"), self.tr(f"El archivo de ajustes no tiene el formato esperado. Falta la clave: {e}"))
            logging.error(f"Error de formato en el archivo de ajustes {file_path}", exc_info=True)



    @gui_error_handler
    def open_bra_dialog(self):
        logging.info("Abriendo diálogo para cargar archivo .bra.")
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Cargar Archivo Braille (.bra)"), "", self.tr("Archivos Braille (*.bra)"))
        if not file_path:
            logging.info("El usuario canceló la carga de archivo .bra.")
            return

        lang_items = [self.tr("Castellano"), self.tr("Catalán")]
        language, ok = QInputDialog.getItem(self, self.tr("Idioma Braille"), self.tr("Selecciona el idioma del Braille:"), lang_items, 0, False)
        if not ok or not language:
            logging.info("El usuario canceló la selección de idioma para archivo .bra.")
            return
        language = language.lower()

        worker = Worker(self._open_bra_task, file_path, language)
        worker.signals.result.connect(self._on_open_bra_result)
        worker.signals.finished.connect(self._task_complete)
        worker.signals.error.connect(self._task_error)
        self.threadpool.start(worker)
        self.statusBar().showMessage(self.tr("Cargando archivo .bra..."), 0)

    def _open_bra_task(self, file_path, language, progress_callback):
        with open(file_path, 'r', encoding='utf-8') as f:
            braille_content = f.read()
        detected_dots_mode = braille_processor.detect_braille_dots_mode(braille_content)
        return braille_content, language, detected_dots_mode

    def _on_open_bra_result(self, result):
        if result is None: return
        braille_content, language, detected_dots_mode = result
        logging.info(f"Archivo .bra cargado: {language}, {detected_dots_mode} puntos.")
        self.braille_dots_mode = detected_dots_mode
        if detected_dots_mode == 6:
            self.action_6_dots.setChecked(True)
        else:
            self.action_8_dots.setChecked(True)

        self.set_ui_mode('braille_file')
        self.original_cv_img = None
        self._save_state()
        self.raw_braille_text = braille_content
        self.reformat_braille_output()
        self.statusBar().showMessage(self.tr(f"Archivo .bra cargado ({language}, {detected_dots_mode} puntos)"), 3000)
        for action in [self.action_save, self.action_copy, self.export_menu, self.action_desbraille, self.action_visualize_braille, self.action_print_braille]:
            action.setEnabled(True)
        self.btn_zoom_in_text.setEnabled(True)
        self.btn_zoom_out_text.setEnabled(True)

    @gui_error_handler
    def open_brf_dialog(self):
        logging.info("Abriendo diálogo para cargar archivo .brf.")
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Cargar Archivo Braille BRF (.brf)"), "", self.tr("Archivos Braille BRF (*.brf)"))
        if not file_path:
            logging.info("El usuario canceló la carga de archivo .brf.")
            return

        lang_items = [self.tr("Castellano"), self.tr("Catalán")]
        language, ok = QInputDialog.getItem(self, self.tr("Idioma Braille"), self.tr("Selecciona el idioma del Braille:"), lang_items, 0, False)
        if not ok or not language:
            logging.info("El usuario canceló la selección de idioma para archivo .brf.")
            return
        language = language.lower()

        worker = Worker(self._open_brf_task, file_path, language)
        worker.signals.result.connect(self._on_open_brf_result)
        worker.signals.finished.connect(self._task_complete)
        worker.signals.error.connect(self._task_error)
        self.threadpool.start(worker)
        self.statusBar().showMessage(self.tr("Cargando archivo .brf..."), 0)

    def _open_brf_task(self, file_path, language, progress_callback):
        with open(file_path, 'r', encoding='ascii') as f:
            brf_content = f.read()
        detected_dots_mode = braille_processor.detect_braille_dots_mode(brf_content)
        return brf_content, language, detected_dots_mode

    def _on_open_brf_result(self, result):
        if result is None: return
        brf_content, language, detected_dots_mode = result
        logging.info(f"Archivo .brf cargado: {language}, {detected_dots_mode} puntos.")
        self.braille_dots_mode = detected_dots_mode
        if detected_dots_mode == 6:
            self.action_6_dots.setChecked(True)
        else:
            self.action_8_dots.setChecked(True)

        self.set_ui_mode('braille_file')
        self.original_cv_img = None
        self._save_state()
        self.raw_braille_text = brf_content
        self.reformat_braille_output()
        self.statusBar().showMessage(self.tr(f"Archivo .brf cargado ({language}, {detected_dots_mode} puntos)"), 3000)
        for action in [self.action_save, self.action_copy, self.export_menu, self.action_desbraille, self.action_visualize_braille, self.action_print_braille]:
            action.setEnabled(True)
        self.btn_zoom_in_text.setEnabled(True)
        self.btn_zoom_out_text.setEnabled(True)

    @gui_error_handler
    def desbraille_braille_text(self):
        braille_text = self.braille_display.toPlainText()
        if not braille_text or braille_text.startswith("Error:"):
            QMessageBox.warning(self, self.tr("Nada que desbraillar"), self.tr("No hay resultado Braille válido para desbraillar."))
            logging.warning("Intento de desbraillar sin contenido válido.")
            return

        format_items = [self.tr("BRA (Unicode)"), self.tr("BRF (ASCII)")]
        input_format, ok = QInputDialog.getItem(self, self.tr("Formato de Entrada"), self.tr("Selecciona el formato del Braille de entrada:"), format_items, 0, False)
        if not ok:
            logging.info("El usuario canceló la selección de formato de entrada para desbraillar.")
            return

        lang_items = [self.tr("Castellano"), self.tr("Catalán")]
        language, ok = QInputDialog.getItem(self, self.tr("Idioma Braille"), self.tr("Selecciona el idioma del Braille:"), lang_items, 0, False)
        if not ok or not language:
            logging.info("El usuario canceló la selección de idioma para desbraillar.")
            return
        language = language.lower()
        logging.info(f"Iniciando desbraillado con formato {input_format} e idioma {language}.")
        worker = Worker(self._desbraille_task, braille_text, input_format, language, self.braille_dots_mode)
        worker.signals.result.connect(self._on_desbraille_result)
        worker.signals.finished.connect(self._task_complete)
        worker.signals.error.connect(self._task_error)
        self.threadpool.start(worker)
        self.statusBar().showMessage(self.tr("Desbrailleando texto..."), 0)

    def _desbraille_task(self, braille_text, input_format, language, dots_mode, progress_callback):
        if "BRF" in input_format:
            return braille_processor.convert_brf_to_text(braille_text, language, dots_mode)
        else:
            return braille_processor.convert_braille_to_text(braille_text, language, dots_mode)

    def _on_desbraille_result(self, plain_text):
        if plain_text is None: return
        logging.info("Desbraillado completado exitosamente.")
        self.latin_display.setText(plain_text)
        self.latin_display.setVisible(True)
        self.statusBar().showMessage(self.tr(f"Texto Braille desbraillado a texto plano ({self.current_language}, {self.braille_dots_mode} puntos)"), 3000)
        for action in [self.action_save, self.action_copy, self.export_menu]:
            action.setEnabled(True)
        self.btn_zoom_in_text.setEnabled(True)
        self.btn_zoom_out_text.setEnabled(True)

    def visualize_braille_text(self, to_bytes=False):
        braille_text = self.braille_display.toPlainText()
        if not braille_text:
            QMessageBox.warning(self, self.tr("Sin Braille"), self.tr("No hay texto Braille para visualizar."))
            return None

        try:
            # Create a QImage to draw the Braille text
            font = QFont("Courier New", 10)
            font_metrics = QFontMetrics(font)
            lines = braille_text.split('\n')
            line_height = font_metrics.height()
            width = max(font_metrics.horizontalAdvance(line) for line in lines)
            height = len(lines) * line_height

            image = QImage(width, height, QImage.Format_RGB32)
            image.fill(Qt.white)

            painter = QPainter(image)
            painter.setFont(font)
            painter.setPen(Qt.black)

            for i, line in enumerate(lines):
                painter.drawText(0, (i + 1) * line_height, line)

            painter.end()

            if to_bytes:
                # Convert QImage to bytes
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.WriteOnly)
                image.save(buffer, "JPG")
                return byte_array.data()
            else:
                # Display the image in a dialog
                pixmap = QPixmap.fromImage(image)
                dialog = QDialog(self)
                dialog.setWindowTitle(self.tr("Visualización de Braille"))
                layout = QVBoxLayout()
                label = QLabel()
                label.setPixmap(pixmap)
                layout.addWidget(label)
                dialog.setLayout(layout)
                dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))
            return None

    def _visualize_braille_task(self, braille_text, dot_size, dot_spacing, bg_color, dot_color, progress_callback):
        braille_image_np = image_processor.convert_braille_to_image(braille_text, dot_size=dot_size, dot_spacing=dot_spacing, background_color=bg_color, dot_color=dot_color)
        return braille_image_np

    def _on_visualize_braille_result(self, braille_image_np):
        if braille_image_np is None: return
        logging.info("Visualización de Braille generada exitosamente.")
        h, w, ch = braille_image_np.shape
        bytes_per_line = ch * w
        qt_image = QImage(braille_image_np.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)

        self.lbl_image_preview.setPixmap(pixmap)
        self.set_ui_mode('image')
        self.statusBar().showMessage(self.tr("Visualización Braille generada"), 3000)

    def update_braille_display_settings(self):
        self.braille_dot_size = self.slider_dot_size.value()
        self.braille_dot_spacing = self.slider_dot_spacing.value()
        self.lbl_dot_size_value.setText(str(self.braille_dot_size))
        self.lbl_dot_spacing_value.setText(str(self.braille_dot_spacing))
        if self.braille_display.toPlainText(): # Only re-visualize if there's braille text
            self.visualize_braille_text()

    def set_braille_color_scheme(self, scheme):
        if scheme == 'default':
            self.braille_bg_color = (0, 0, 0)      # Black background
            self.braille_dot_color = (255, 255, 255) # White dots
        elif scheme == 'inverted':
            self.braille_bg_color = (255, 255, 255) # White background
            self.braille_dot_color = (0, 0, 0)      # Black dots
        
        if self.braille_display.toPlainText(): # Only re-visualize if there's braille text
            self.visualize_braille_text()

    def open_braille_text_editor(self):
        if not self.raw_braille_text:
            QMessageBox.warning(self, self.tr("Sin texto Braille"), self.tr("No hay texto Braille para editar. Carga una imagen o texto primero."))
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Editor de Texto Braille"))
        dialog.setModal(True)
        dialog_layout = QVBoxLayout(dialog)

        editor = BrailleTextEditor(self.raw_braille_text, self.current_language, self.braille_dots_mode, dialog)
        dialog_layout.addWidget(editor)

        # Add OK/Cancel buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton(self.tr("Aceptar"))
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton(self.tr("Cancelar"))
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        dialog_layout.addLayout(button_layout)

        if dialog.exec() == QDialog.Accepted:
            new_braille_text = editor.get_braille_text()
            if new_braille_text != self.raw_braille_text:
                self.raw_braille_text = new_braille_text
                self.reformat_braille_output()
                self._save_state()
                self.statusBar().showMessage(self.tr("Texto Braille actualizado desde el editor."), 3000)

    def open_braille_printer_dialog(self):
        if not self.raw_braille_text:
            QMessageBox.warning(self, self.tr("Sin texto Braille"), self.tr("No hay texto Braille para imprimir. Carga una imagen o texto primero."))
            return

        dialog = BraillePrinterDialog(self.braille_dots_mode, self)
        # Pass the raw_braille_text to the dialog for potential test printing
        dialog.braille_text_to_print = self.raw_braille_text

        if dialog.exec() == QDialog.Accepted:
            settings = dialog.get_settings()
            logging.info(f"Configuración de impresora Braille seleccionada: {settings}")
            self._print_braille_file(self.raw_braille_text, settings)

    @gui_error_handler
    def _print_braille_file(self, braille_text, settings):
        import tempfile
        import os
        try:
            printer_name = settings.get("printer_name")
            lines_per_page = settings.get("lines_per_page")
            chars_per_line = settings.get("chars_per_line")
            interpoint = settings.get("interpoint")
            output_format = settings.get("output_format")
            dots_mode = settings.get("dots_mode") # Get dots_mode for BRF conversion

            if not printer_name:
                raise ValueError(self.tr("No se seleccionó ninguna impresora."))
            if not lines_per_page or not chars_per_line:
                raise ValueError(self.tr("Configuración de página inválida."))

            logging.info(f"Impresora seleccionada: {printer_name}")
            logging.info(f"Configuración de impresión: Líneas/página={lines_per_page}, Caracteres/línea={chars_per_line}, Interpunto={interpoint}, Formato={output_format}")

            final_output_text = ""
            temp_file_suffix = ".txt"
            file_encoding = 'utf-8'
            doc_data_type = "RAW" # Default for raw Braille

            if output_format == "brf":
                # BRF conversion requires the original braille_text (Unicode) and dots_mode
                # The _format_braille_for_printer function already handles line/page breaks
                # so we apply it first, then convert to BRF.
                formatted_braille_text = self._format_braille_for_printer(braille_text, lines_per_page, chars_per_line, interpoint)
                final_output_text = braille_processor.convert_unicode_to_brf_string(formatted_braille_text, self.current_language, dots_mode)
                temp_file_suffix = ".brf"
                file_encoding = 'ascii' # BRF files are typically ASCII
                doc_data_type = "TEXT" # Some drivers might handle BRF as TEXT
            else: # unicode_txt
                final_output_text = self._format_braille_for_printer(braille_text, lines_per_page, chars_per_line, interpoint)
                temp_file_suffix = ".txt"
                file_encoding = 'utf-8'
                doc_data_type = "RAW"

            # Create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding=file_encoding, suffix=temp_file_suffix) as temp_file:
                temp_file.write(final_output_text)
                temp_file_path = temp_file.name

            logging.info(f"Archivo temporal creado para impresión: {temp_file_path}")

            # Open the printer
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                # Start a print job
                doc_info = ("Braille Output", None, doc_data_type)
                hJob = win32print.StartDocPrinter(hPrinter, 1, doc_info)
                try:
                    win32print.StartPagePrinter(hPrinter)
                    with open(temp_file_path, 'rb') as f:
                        data = f.read()
                        win32print.WritePrinter(hPrinter, data)
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)

            self.statusBar().showMessage(self.tr(f"Enviando a impresora Braille: {printer_name}"), 5000)
            QMessageBox.information(self, self.tr("Impresión Enviada"), self.tr(f"El texto Braille ha sido enviado a la impresora '{printer_name}'. Asegúrate de que la impresora esté encendida y conectada."))
            logging.info(f"Texto Braille enviado a la impresora: {printer_name}")

        except Exception as e:
            logging.error(f"Error al imprimir el archivo Braille: {e}", exc_info=True)
            QMessageBox.critical(self, self.tr("Error de Impresión"), self.tr(f"No se pudo enviar el texto a la impresora Braille.\nError: {e}\nAsegúrate de que la impresora esté correctamente instalada y configurada como predeterminada."))
        finally:
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logging.info(f"Archivo temporal eliminado: {temp_file_path}")

    def _format_braille_for_printer(self, braille_text, lines_per_page, chars_per_line, interpoint):
        formatted_lines = []
        current_page_lines = []
        
        # Split the input braille text into paragraphs/lines based on existing newlines
        paragraphs = braille_text.split('\n')

        for para in paragraphs:
            words = para.split(' ')
            current_line_content = ""
            for word in words:
                # Check if adding the next word exceeds chars_per_line
                # +1 for the space before the word
                if len(current_line_content) + len(word) + (1 if current_line_content else 0) > chars_per_line:
                    current_page_lines.append(current_line_content)
                    current_line_content = word
                else:
                    if current_line_content:
                        current_line_content += " " + word
                    else:
                        current_line_content = word
            if current_line_content:
                current_page_lines.append(current_line_content)
            
            # Add an empty line for paragraph separation if not at the end of a page
            if current_page_lines and len(current_page_lines) % lines_per_page != 0:
                current_page_lines.append("")

            # Check for page breaks
            while len(current_page_lines) >= lines_per_page:
                for i in range(lines_per_page):
                    formatted_lines.append(current_page_lines.pop(0))
                # Add form feed character for page break
                formatted_lines.append('\f') 
        
        # Add any remaining lines to the last page
        for line in current_page_lines:
            formatted_lines.append(line)

        # Remove trailing form feed if it's the very last character
        if formatted_lines and formatted_lines[-1] == '\f':
            formatted_lines.pop()

        return '\n'.join(formatted_lines)

    def open_braille_learning_dialog(self):
        logging.info("Abriendo modo de aprendizaje interactivo de Braille.")
        dialog = BrailleLearningDialog(self.current_language, self.braille_dots_mode, self)
        dialog.exec()
        logging.info("Modo de aprendizaje interactivo de Braille cerrado.")

    def open_custom_braille_table_dialog(self):
        logging.info("Abriendo diálogo de gestión de tablas Braille personalizadas.")
        dialog = CustomBrailleTableDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.custom_braille_tables = dialog.get_custom_tables()
            logging.info(f"Tablas Braille personalizadas actualizadas: {self.custom_braille_tables.keys()}")
            # Re-evaluate language menu to include custom tables
            self.update_language_menu()

    def reformat_braille_output(self):
        if not hasattr(self, 'plain_text_content') or not self.plain_text_content:
            # If there's no plain text content, we might be in image mode or braille file mode
            # In these cases, raw_braille_text is already set, so just display it.
            if not hasattr(self, 'raw_braille_text'):
                return
            # If raw_braille_text exists, proceed to display it without re-conversion
        else:
            # Re-convert plain text to braille with the current dots mode
            self.raw_braille_text = braille_processor.convert_text_to_braille(self.plain_text_content, self.current_language, self.braille_dots_mode)

        if self.action_no_split_words.isChecked():
            chars_per_line = 38
            margin = " "
            
            output_lines = [''] # Top margin

            paragraphs = self.raw_braille_text.split('\n')
            
            for para in paragraphs:
                words = para.split(' ')
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 > chars_per_line:
                        output_lines.append(margin + current_line)
                        current_line = word
                    else:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                if current_line:
                    output_lines.append(margin + current_line)
            
            output_lines.append('') # Bottom margin
            
            self.braille_display.setText('\n'.join(output_lines))
        else:
            self.braille_display.setText(self.raw_braille_text)

    def close_file(self):
        logging.info("Cerrando archivo y reseteando la interfaz.")
        self.original_cv_img = None
        self.raw_braille_text = ""
        self.plain_text_content = ""
        self.image_path = None
        self.braille_display.clear()
        self.latin_display.clear()
        self.lbl_image_preview.setPixmap(QPixmap())
        self.lbl_image_preview.setText(self.tr("Arrastra una imagen aquí o cárgala desde el menú Archivo"))
        self.set_ui_mode('initial_state')
        self.enable_initial_actions(True)
        self._save_state() # Save the clean state

    def undo(self):
        if len(self.undo_stack) > 1: # Keep the initial state
            self.redo_stack.append(self.undo_stack.pop())
            state_to_restore = self.undo_stack[-1]
            self.restore_state(state_to_restore)
            logging.info("Acción deshecha.")
        else:
            logging.warning("No hay más acciones que deshacer.")

    def redo(self):
        if self.redo_stack:
            state_to_restore = self.redo_stack.pop()
            self.undo_stack.append(state_to_restore)
            self.restore_state(state_to_restore)
            logging.info("Acción rehecha.")
        else:
            logging.warning("No hay más acciones que rehacer.")

    def _save_state(self):
        # This method should be called after any action that changes the application state
        current_state = self.get_current_state()
        # Avoid saving consecutive duplicate states
        if not self.undo_stack or self.undo_stack[-1] != current_state:
            self.undo_stack.append(current_state)
            self.redo_stack.clear() # Clear redo stack on any new action
            logging.debug("Estado guardado para deshacer.")


    def get_current_state(self):
        # Obtener los parámetros de los filtros desde el panel
        filter_params = self.filter_settings_panel.get_parameters()

        state = {
            'original_cv_img': self.original_cv_img.copy() if self.original_cv_img is not None else None,
            'braille_text': self.raw_braille_text,
            'brightness': self.slider_brightness.value(),
            'contrast': self.slider_contrast.value(),
            'inverted': self.action_invert.isChecked(),
            'dithering': self.action_dithering.isChecked(),
            'lines': self.action_lines.isChecked(),
            'adaptive_thresholding': self.action_adaptive_thresholding.isChecked(),
            'remove_noise': self.action_remove_noise.isChecked(),
            'color_mode': self.current_color_mode,
            'active_color_filters': list(self.active_color_filters),
            'noise_reduction_filter': self.current_noise_reduction_filter,
            'edge_detection_algorithm': self.current_edge_detection_algorithm,
            'segmentation_algorithm': self.current_segmentation_algorithm,
            'segmentation_rect': self.segmentation_rect,
        }
        # Añadir los parámetros de los filtros al estado
        state.update(filter_params)

    def restore_state(self, state):
        logging.info("Restaurando estado anterior.")
        self.raw_braille_text = state['braille_text']
        self.plain_text_content = state['plain_text_content']
        self.image_path = state['image_path']
        # self.original_cv_img is not restored from state, it's managed separately
        
        # Temporarily disconnect signals to avoid triggering updates during restore
        self.slider_brightness.valueChanged.disconnect()
        self.slider_contrast.valueChanged.disconnect()
        self.action_invert.triggered.disconnect()
        self.action_dithering.triggered.disconnect()
        self.action_lines.triggered.disconnect()
        self.action_adaptive_thresholding.triggered.disconnect()
        self.action_remove_noise.triggered.disconnect()
        self.action_color_original.triggered.disconnect()
        self.action_color_grayscale.triggered.disconnect()
        self.action_color_red.triggered.disconnect()
        self.action_color_green.triggered.disconnect()
        self.action_color_blue.triggered.disconnect()
        self.action_noise_none.triggered.disconnect()
        self.action_noise_median.triggered.disconnect()
        self.action_noise_gaussian.triggered.disconnect()
        self.action_noise_bilateral.triggered.disconnect()
        self.action_edge_none.triggered.disconnect()
        self.action_edge_canny.triggered.disconnect()
        self.action_edge_sobel.triggered.disconnect()
        self.action_edge_prewitt.triggered.disconnect()
        self.action_edge_laplacian.triggered.disconnect()

        self.slider_brightness.setValue(state['brightness'])
        self.slider_contrast.setValue(state['contrast'])
        self.action_invert.setChecked(state['inverted'])
        self.action_dithering.setChecked(state.get('dithering', False))
        self.action_lines.setChecked(state.get('lines_mode', False))
        self.action_adaptive_thresholding.setChecked(state.get('adaptive_thresholding', False))
        self.action_remove_noise.setChecked(state.get('remove_noise', False))
        self.current_color_mode = state.get('current_color_mode', 'original')
        self.action_color_original.setChecked(self.current_color_mode == 'original')
        self.action_color_grayscale.setChecked(self.current_color_mode == 'grayscale')
        self.active_color_filters = state.get('active_color_filters', [])
        self.action_color_red.setChecked('red' in self.active_color_filters)
        self.action_color_green.setChecked('green' in self.active_color_filters)
        self.action_color_blue.setChecked('blue' in self.active_color_filters)
        self.current_noise_reduction_filter = state.get('current_noise_reduction_filter', 'none')
        self.action_noise_none.setChecked(self.current_noise_reduction_filter == 'none')
        self.action_noise_median.setChecked(self.current_noise_reduction_filter == 'median')
        self.action_noise_gaussian.setChecked(self.current_noise_reduction_filter == 'gaussian')
        self.action_noise_bilateral.setChecked(self.current_noise_reduction_filter == 'bilateral')
        self.current_edge_detection_algorithm = state.get('current_edge_detection_algorithm', 'none')
        self.action_edge_none.setChecked(self.current_edge_detection_algorithm == 'none')
        self.action_edge_canny.setChecked(self.current_edge_detection_algorithm == 'canny')
        self.action_edge_sobel.setChecked(self.current_edge_detection_algorithm == 'sobel')
        self.action_edge_prewitt.setChecked(self.current_edge_detection_algorithm == 'prewitt')
        self.action_edge_laplacian.setChecked(self.current_edge_detection_algorithm == 'laplacian')

        # Restaurar los parámetros en el panel de filtros
        self.filter_settings_panel.set_parameters(state)
        
        # Reconnect signals
        self.slider_brightness.valueChanged.connect(self.update_all_previews)
        self.slider_contrast.valueChanged.connect(self.update_all_previews)
        self.action_invert.triggered.connect(lambda: self.update_all_previews())
        self.action_dithering.triggered.connect(lambda: self.update_all_previews())
        self.action_lines.triggered.connect(lambda: self.update_all_previews())
        self.action_adaptive_thresholding.triggered.connect(lambda: self.update_all_previews())
        self.action_remove_noise.triggered.connect(self.remove_noise)
        self.action_color_original.triggered.connect(lambda: self.set_color_mode('original'))
        self.action_color_grayscale.triggered.connect(lambda: self.set_color_mode('grayscale'))
        self.action_color_red.triggered.connect(lambda: self.toggle_color_filter('red', self.action_color_red.isChecked()))
        self.action_color_green.triggered.connect(lambda: self.toggle_color_filter('green', self.action_color_green.isChecked()))
        self.action_color_blue.triggered.connect(lambda: self.toggle_color_filter('blue', self.action_color_blue.isChecked()))
        self.action_noise_none.triggered.connect(lambda: self.set_noise_reduction_filter('none'))
        self.action_noise_median.triggered.connect(lambda: self.set_noise_reduction_filter('median'))
        self.action_noise_gaussian.triggered.connect(lambda: self.set_noise_reduction_filter('gaussian'))
        self.action_noise_bilateral.triggered.connect(lambda: self.set_noise_reduction_filter('bilateral'))
        self.action_edge_none.triggered.connect(lambda: self.set_edge_detection_algorithm('none'))
        self.action_edge_canny.triggered.connect(lambda: self.set_edge_detection_algorithm('canny'))
        self.action_edge_sobel.triggered.connect(lambda: self.set_edge_detection_algorithm('sobel'))
        self.action_edge_prewitt.triggered.connect(lambda: self.set_edge_detection_algorithm('prewitt'))
        self.action_edge_laplacian.triggered.connect(lambda: self.set_edge_detection_algorithm('laplacian'))

        # Reconnect signals for filter parameters
        self.action_noise_none.triggered.connect(lambda: self.set_noise_reduction_filter('none'))
        self.action_noise_median.triggered.connect(lambda: self.set_noise_reduction_filter('median'))
        self.action_noise_gaussian.triggered.connect(lambda: self.set_noise_reduction_filter('gaussian'))
        self.action_noise_bilateral.triggered.connect(lambda: self.set_noise_reduction_filter('bilateral'))
        self.action_edge_none.triggered.connect(lambda: self.set_edge_detection_algorithm('none'))
        self.action_edge_canny.triggered.connect(lambda: self.set_edge_detection_algorithm('canny'))
        self.action_edge_sobel.triggered.connect(lambda: self.set_edge_detection_algorithm('sobel'))
        self.action_edge_prewitt.triggered.connect(lambda: self.set_edge_detection_algorithm('prewitt'))
        self.action_edge_laplacian.triggered.connect(lambda: self.set_edge_detection_algorithm('laplacian'))

        self.braille_dots_mode = state['braille_dots_mode']
        setattr(self, 'current_language', state['current_language'])

        # Update UI elements based on restored state
        self.reformat_braille_output()
        self.update_all_previews() # This will also update the image display

        # Update dot mode menu actions
        if self.braille_dots_mode == 6:
            self.action_6_dots.setChecked(True)
        else:
            self.action_8_dots.setChecked(True)

        # Update UI mode based on whether an image is present
        if self.original_cv_img is not None:
            self.set_ui_mode('image')
        elif self.plain_text_content or self.raw_braille_text:
            self.set_ui_mode('text')
        else:
            self.set_ui_mode('initial_state')

        self.statusBar().showMessage(self.tr("Estado restaurado"), 2000)


    def update_language_menu(self):
        # Clear existing custom language actions
        for action in self.custom_language_actions:
            self.language_menu.removeAction(action)
            self.lang_group.removeAction(action)
        self.custom_language_actions.clear()

        # Add custom table languages
        if self.custom_braille_tables:
            self.language_menu.addSeparator()
            for table_name, table_data in self.custom_braille_tables.items():
                action = QAction(table_name, self)
                action.setCheckable(True)
                action.triggered.connect(lambda checked, name=table_name: self.set_language(name))
                self.lang_group.addAction(action)
                self.language_menu.addAction(action)
                self.custom_language_actions.append(action)

        # Ensure the currently selected language is checked
        for action in self.lang_group.actions():
            if action.text() == self.current_language or (action.data() == self.current_language and action.data() is not None):
                action.setChecked(True)
            else:
                action.setChecked(False)

    def set_language(self, lang_code):
        logging.info(f"Cambiando idioma a: {lang_code}")
        # Remove previous translator
        if self.translator:
            QApplication.instance().removeTranslator(self.translator)

        # Load new translator for UI elements
        self.translator = QTranslator()
        if self.translator.load(f"braille_{lang_code}", "translations"):
            QApplication.instance().installTranslator(self.translator)
            self.current_language = lang_code
            self.retranslate_ui()
            
            # Save language setting
            settings = QSettings("BrailleApp", "BrailleConverter")
            settings.setValue("language", lang_code)

            # Update checked state of language actions
            for action in self.lang_group.actions():
                action.setChecked(False)
            if lang_code == 'es': self.action_lang_es.setChecked(True)
            elif lang_code == 'ca': self.action_lang_ca.setChecked(True)
            elif lang_code == 'eu': self.action_lang_eu.setChecked(True)
            elif lang_code == 'gl': self.action_lang_gl.setChecked(True)
            elif lang_code == 'en': self.action_lang_en.setChecked(True)
            # For custom languages, the action text is the table name, so we check by text
            for action in self.custom_language_actions:
                if action.text() == lang_code:
                    action.setChecked(True)
        else:
            logging.warning(f"No se pudo cargar la traducción para {lang_code}. Intentando con idioma por defecto.")
            # If a custom table is selected, we don't have a .qm file for it, so we just set the current_language
            if lang_code in self.custom_braille_tables:
                self.current_language = lang_code
                settings = QSettings("BrailleApp", "BrailleConverter")
                settings.setValue("language", lang_code)
                for action in self.lang_group.actions():
                    action.setChecked(False)
                for action in self.custom_language_actions:
                    if action.text() == lang_code:
                        action.setChecked(True)
            else:
                logging.warning(f"No se pudo cargar la traducción para {lang_code}. Revertiendo a español.")
                self.set_language('es') # Fallback to Spanish

    def set_theme(self, theme_name):
        logging.info(f"Cambiando tema a: {theme_name}")
        # Apply stylesheet based on theme_name
        stylesheet = ""
        if theme_name == 'dark':
            stylesheet = """
                QMainWindow { background-color: #2b2b2b; color: #f0f0f0; }
                QWidget { background-color: #2b2b2b; color: #f0f0f0; }
                QMenuBar { background-color: #3c3c3c; color: #f0f0f0; }
                QMenu { background-color: #3c3c3c; color: #f0f0f0; }
                QMenu::item:selected { background-color: #555555; }
                QTextEdit { background-color: #1e1e1e; color: #f0f0f0; border: 1px solid #555555; }
                QLabel { color: #f0f0f0; }
                QPushButton { background-color: #555555; color: #f0f0f0; border: 1px solid #777777; padding: 5px; }
                QPushButton:hover { background-color: #666666; }
                QSlider::groove:horizontal { border: 1px solid #555555; height: 8px; background: #3c3c3c; margin: 2px 0; }
                QSlider::handle:horizontal { background: #f0f0f0; border: 1px solid #777777; width: 18px; margin: -2px 0px; border-radius: 3px; }
                QScrollArea { background-color: #2b2b2b; }
            """
        elif theme_name == 'light':
            stylesheet = """
                QMainWindow { background-color: #f0f0f0; color: #1e1e1e; }
                QWidget { background-color: #f0f0f0; color: #1e1e1e; }
                QMenuBar { background-color: #e0e0e0; color: #1e1e1e; }
                QMenu { background-color: #e0e0e0; color: #1e1e1e; }
                QMenu::item:selected { background-color: #cccccc; }
                QTextEdit { background-color: #ffffff; color: #1e1e1e; border: 1px solid #aaaaaa; }
                QLabel { color: #1e1e1e; }
                QPushButton { background-color: #e0e0e0; color: #1e1e1e; border: 1px solid #aaaaaa; padding: 5px; }
                QPushButton:hover { background-color: #d0d0d0; }
                QSlider::groove:horizontal { border: 1px solid #aaaaaa; height: 8px; background: #e0e0e0; margin: 2px 0; }
                QSlider::handle:horizontal { background: #1e1e1e; border: 1px solid #aaaaaa; width: 18px; margin: -2px 0px; border-radius: 3px; }
                QScrollArea { background-color: #f0f0f0; }
            """
        elif theme_name == 'high_contrast':
            stylesheet = """
                QMainWindow { background-color: black; color: yellow; }
                QWidget { background-color: black; color: yellow; }
                QMenuBar { background-color: black; color: yellow; }
                QMenu { background-color: black; color: yellow; }
                QMenu::item:selected { background-color: #333300; }
                QTextEdit { background-color: black; color: yellow; border: 1px solid yellow; }
                QLabel { color: yellow; }
                QPushButton { background-color: black; color: yellow; border: 1px solid yellow; padding: 5px; }
                QPushButton:hover { background-color: #333300; }
                QSlider::groove:horizontal { border: 1px solid yellow; height: 8px; background: black; margin: 2px 0; }
                QSlider::handle:horizontal { background: yellow; border: 1px solid yellow; width: 18px; margin: -2px 0px; border-radius: 3px; }
                QScrollArea { background-color: black; }
            """
        # 'system' theme means no custom stylesheet, revert to default
        QApplication.instance().setStyleSheet(stylesheet)

        # Update the checked state of the theme actions
        for action in self.theme_group.actions():
            action.setChecked(False)
        if theme_name == 'system': self.action_theme_system.setChecked(True)
        elif theme_name == 'dark': self.action_theme_dark.setChecked(True)
        elif theme_name == 'light': self.action_theme_light.setChecked(True)
        elif theme_name == 'high_contrast': self.action_theme_high_contrast.setChecked(True)

        # Save theme setting
        settings = QSettings("BrailleApp", "BrailleConverter")
        settings.setValue("theme", theme_name)

    def set_font_size(self, font_size):
        logging.info(f"Cambiando tamaño de fuente a: {font_size}")
        # Apply font size to the entire application
        app = QApplication.instance()
        if font_size == 'system':
            # Reset to default system font
            app.setFont(self.default_app_font)
        else:
            # Apply specified font size
            current_font = app.font()
            current_font.setPointSize(font_size)
            app.setFont(current_font)

        # Update the checked state of the font size actions
        for action in self.font_size_group.actions():
            action.setChecked(False)
        if font_size == 'system': self.action_font_size_system.setChecked(True)
        elif font_size == 14: self.action_font_size_14.setChecked(True)
        elif font_size == 16: self.action_font_size_16.setChecked(True)
        elif font_size == 18: self.action_font_size_18.setChecked(True)
        elif font_size == 22: self.action_font_size_22.setChecked(True)
        elif font_size == 32: self.action_font_size_32.setChecked(True)

        # Save font size setting
        settings = QSettings("BrailleApp", "BrailleConverter")
        settings.setValue("font_size", font_size)

    def set_braille_dots_mode(self, mode):
        logging.info(f"Cambiando modo de puntos a: {mode}")
        self.braille_dots_mode = mode
        
        # Update checked state of menu actions
        if self.action_6_dots: self.action_6_dots.setChecked(mode == 6)
        if self.action_8_dots: self.action_8_dots.setChecked(mode == 8)

        # Save dots mode setting
        settings = QSettings("BrailleApp", "BrailleConverter")
        settings.setValue("braille_dots_mode", mode)

        # Reformat braille output if there is any
        if self.raw_braille_text or self.plain_text_content:
            self.reformat_braille_output()

    def set_color_mode(self, mode):
        logging.info(f"Cambiando modo de color a: {mode}")
        self.current_color_mode = mode
        self.update_all_previews()

        # Save color mode setting
        settings = QSettings("BrailleApp", "BrailleConverter")
        settings.setValue("color_mode", mode)

        # Update checked state of menu actions
        self.action_color_original.setChecked(mode == 'original')
        self.action_color_grayscale.setChecked(mode == 'grayscale')

        # Clear individual color filters if 'original' or 'grayscale' is selected
        if mode == 'original' or mode == 'grayscale':
            self.active_color_filters.clear()
            self.action_color_red.setChecked(False)
            self.action_color_green.setChecked(False)
            self.action_color_blue.setChecked(False)

    def set_noise_reduction_filter(self, filter_type):
        """Establece el filtro de reducción de ruido y actualiza la UI."""
        self.current_noise_reduction_filter = filter_type
        logging.info(f"Filtro de reducción de ruido cambiado a: {filter_type}")

        # Muestra el panel de ajustes apropiado
        self.filter_settings_panel.show_filter_group(filter_type)

        self.update_all_previews()
        self._save_state()

    def set_edge_detection_algorithm(self, algorithm):
        """Establece el algoritmo de detección de bordes y actualiza la UI."""
        self.current_edge_detection_algorithm = algorithm
        logging.info(f"Algoritmo de detección de bordes cambiado a: {algorithm}")
        
        # Muestra el panel de ajustes apropiado
        self.filter_settings_panel.show_filter_group(algorithm)

        self.update_all_previews()
        self._save_state()

    def toggle_color_filter(self, color, checked):
        if checked:
            if color not in self.active_color_filters:
                self.active_color_filters.append(color)
            # Uncheck 'original' and 'grayscale' if an individual color filter is selected
            self.action_color_original.setChecked(False)
            self.action_color_grayscale.setChecked(False)
            self.current_color_mode = 'filtered' # Indicate that individual filters are active
        else:
            if color in self.active_color_filters:
                self.active_color_filters.remove(color)
            if not self.active_color_filters: # If no filters are active, revert to original
                self.set_color_mode('original')

        self.update_all_previews()

        # Save active color filters
        settings = QSettings("BrailleApp", "BrailleConverter")
        settings.setValue("active_color_filters", self.active_color_filters)

    def update_recent_files_menu(self):
        for action in self.recent_file_actions:
            self.recent_files_menu.removeAction(action)
        self.recent_file_actions.clear()

        settings = QSettings("BrailleApp", "BrailleConverter")
        recent_files = settings.value("recentFiles", [])

        for file_path in recent_files:
            if file_path:
                action = QAction(os.path.basename(file_path), self)
                action.setData(file_path)
                action.triggered.connect(self.open_recent_file)
                self.recent_files_menu.addAction(action)
                self.recent_file_actions.append(action)

        self.recent_files_menu.addSeparator()
        clear_action = QAction(self.tr("Limpiar Menú"), self)
        clear_action.triggered.connect(self.clear_recent_files)
        self.recent_files_menu.addAction(clear_action)
        self.recent_file_actions.append(clear_action)

    def add_to_recent_files(self, file_path):
        settings = QSettings("BrailleApp", "BrailleConverter")
        recent_files = settings.value("recentFiles", [])
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        if len(recent_files) > self.max_recent_files:
            recent_files.pop()
        settings.setValue("recentFiles", recent_files)
        self.update_recent_files_menu()

    def open_recent_file(self):
        action = self.sender()
        if action:
            file_path = action.data()
            _, extension = os.path.splitext(file_path)
            if extension.lower() in self.supported_image_extensions:
                self.load_image(file_path)
            else:
                items = [self.tr("Castellano Grado 1"), self.tr("Catalán Grado 1")]
                item, ok = QInputDialog.getItem(self, self.tr("Seleccionar Tabla Braille"), self.tr("Elige la tabla de conversión:"), items, 0, False)
                if ok and item:
                    language = 'catalan' if item == self.tr("Catalán Grado 1") else 'spanish'
                    self.load_text(file_path, is_file=True, language=language)

    def clear_recent_files(self):
        settings = QSettings("BrailleApp", "BrailleConverter")
        settings.setValue("recentFiles", [])
        self.update_recent_files_menu()
