
import pytest
import numpy as np
import image_processor

@pytest.fixture
def black_image():
    """Crea una imagen de prueba negra de 8x8 píxeles."""
    return np.zeros((8, 8), dtype=np.uint8)

@pytest.fixture
def white_image():
    """Crea una imagen de prueba blanca de 8x8 píxeles."""
    return np.full((8, 8), 255, dtype=np.uint8)

def test_convert_image_to_braille_black(black_image):
    """Verifica que una imagen negra se convierte en espacios Braille."""
    # Ancho de salida de 2 caracteres Braille (4 píxeles en la imagen reescalada)
    braille_text = image_processor.convert_image_to_braille(
        black_image, width=2, contrast=1.0, brightness=0, 
        is_inverted=False, use_dithering=False, dots_mode=8, 
        use_adaptive_thresholding=False
    )
    # La imagen de 8x8 se reescala a 4x4. Esto da 1 fila de 2 caracteres.
    # Como la imagen es negra, el umbral la deja en 0, y los caracteres son vacíos.
    expected_output = "\u2800\u2800"
    assert braille_text == expected_output

def test_convert_image_to_braille_white(white_image):
    """Verifica que una imagen blanca se convierte en celdas Braille completas."""
    braille_text = image_processor.convert_image_to_braille(
        white_image, width=2, contrast=1.0, brightness=0, 
        is_inverted=False, use_dithering=False, dots_mode=8, 
        use_adaptive_thresholding=False
    )
    # La imagen blanca se convierte en 1s, y con 8 puntos, el carácter es \u28ff
    expected_output = "\u28ff\u28ff"
    assert braille_text == expected_output
