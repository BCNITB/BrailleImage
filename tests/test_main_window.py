
import pytest
from PySide6.QtCore import Qt
from ui.main_window import MainWindow

# Marca todos los tests de este fichero para que se ejecuten con el plugin de qt
@pytest.mark.qt
def test_main_window_initialization(qtbot):
    """Test to verify the main window initializes correctly."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    # Verificar que la ventana es visible
    assert window.isVisible()

    # Verificar que el título es el esperado
    # Usamos el texto original, ya que la traducción puede no estar cargada en el entorno de test
    assert window.windowTitle() == "Conversor a Braille"
