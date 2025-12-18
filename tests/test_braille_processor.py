
import pytest
import braille_processor

# Datos de prueba: (carácter, patrón de puntos esperado)
# El patrón de puntos es un entero donde cada bit representa un punto.
# Punto 1 -> bit 0 (1), Punto 2 -> bit 1 (2), etc.
TEST_DATA = [
    ('a', 1),          # Punto 1
    ('b', 3),          # Puntos 1 y 2
    ('c', 9),          # Puntos 1 y 4
    ('z', 53),         # Puntos 1, 3, 5, 6 (Corregido)
    ('.', 2),          # Puntos 2 (Corregido)
    (' ', 0),          # Espacio
]

@pytest.mark.parametrize("char, expected_pattern", TEST_DATA)
def test_get_dot_pattern(char, expected_pattern):
    """Verifica que la conversión de carácter a patrón de puntos es correcta."""
    pattern = braille_processor.get_dot_pattern(char)
    assert pattern == expected_pattern

    @pytest.mark.parametrize("expected_char, pattern", TEST_DATA)
    def test_get_char_from_dot_pattern(expected_char, pattern): 
        """Verifica que la conversión de patrón de puntos a carácter es correcta."""
        char = braille_processor.get_char_from_dot_pattern(pattern)

        # Casos especiales con ambigüedad
        if pattern == 2: # Puede ser '.' o ','
            assert char in ['.', ',']
        elif pattern == 0: # Espacio
            assert char in [' ', '\x00']
        else:
            assert char == expected_char
def test_convert_simple_text_to_braille():
    """Verifica la conversión de una cadena de texto simple a Braille."""
    text = "abc"
    # Esperado: carácter braille para 'a', 'b', 'c'
    expected_braille = "\u2801\u2803\u2809"
    braille_text = braille_processor.convert_text_to_braille(text, 'spanish', 6)
    assert braille_text == expected_braille
