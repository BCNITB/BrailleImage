import cv2
import numpy as np
import logging

# --- LÓGICA DE TEXTO A BRAILLE ---

# Tabla de conversión a Braille Grado 1, basada en el estándar literario español.
SPANISH_GRADE_1_MAP = {
    'a': '\u2801', 'b': '\u2803', 'c': '\u2809', 'd': '\u2819', 'e': '\u2811', 'f': '\u280b', 'g': '\u281b', 'h': '\u2813', 'i': '\u280a', 'j': '\u281a',
    'k': '\u2805', 'l': '\u2807', 'm': '\u280d', 'n': '\u281d', 'o': '\u2815', 'p': '\u280f', 'q': '\u281f', 'r': '\u2817', 's': '\u280e', 't': '\u281e',
    'u': '\u2825', 'v': '\u2827', 'w': '\u283a', 'x': '\u282d', 'y': '\u283d', 'z': '\u2835', 'ñ': '\u283b',
    'á': '\u2816', 'é': '\u2826', 'í': '\u280c', 'ó': '\u282c', 'ú': '\u2836', 'ü': '\u283a',
    '1': '\u2801', '2': '\u2803', '3': '\u2809', '4': '\u2819', '5': '\u2811', '6': '\u280b', '7': '\u281b', '8': '\u2813', '9': '\u280a', '0': '\u281a',
    '.': '\u2802', ',': '\u2802', ';': '\u2806', ':': '\u2812', '?': '\u2826', '¿': '\u2826', '!': '\u2816', '¡': '\u2816', '(': '\u2817', ')': '\u2834', '-': '\u2824', '"': '\u2826'
}

CATALAN_GRADE_1_MAP = SPANISH_GRADE_1_MAP.copy()
CATALAN_GRADE_1_MAP.update({
    'ç': '\u282f',      # Ce trencada
    '·': '\u2808',      # Punt volat
    'l·l': '\u2807\u2808\u2807', # l·l (ela geminada)
    'à': '\u2816', 'è': '\u2826', 'é': '\u280c', 'í': '\u280c', 'ï': '\u283a', 'ò': '\u282c', 'ó': '\u2817', 'ú': '\u283a', 'ü': '\u283a'
})

EUSKERA_GRADE_1_MAP = SPANISH_GRADE_1_MAP.copy()
# Add Euskera specific characters here if any

GALICIAN_GRADE_1_MAP = SPANISH_GRADE_1_MAP.copy()
# Add Galician specific characters here if any

BRAILLE_CAPITAL_SIGN = '\u2828'
BRAILLE_NUMBER_SIGN = '\u283c'

# 8-dot Braille maps (example extensions)
SPANISH_8_DOT_MAP = SPANISH_GRADE_1_MAP.copy()
SPANISH_8_DOT_MAP.update({
    '@': chr(0x2800 + 0x40 + 0x01), # Example: Dot 7 + Dot 1
    '#': chr(0x2800 + 0x40 + 0x03), # Example: Dot 7 + Dots 1, 2
    # Add more 8-dot specific characters here
})

CATALAN_8_DOT_MAP = CATALAN_GRADE_1_MAP.copy()
CATALAN_8_DOT_MAP.update({
    '@': chr(0x2800 + 0x40 + 0x01), # Example: Dot 7 + Dot 1
    '#': chr(0x2800 + 0x40 + 0x03), # Example: Dot 7 + Dots 1, 2
    # Add more 8-dot specific characters here
})

EUSKERA_8_DOT_MAP = SPANISH_8_DOT_MAP.copy()
GALICIAN_8_DOT_MAP = SPANISH_8_DOT_MAP.copy()

# Invertir los mapas para la conversión de Braille a texto
def _create_reverse_map(forward_map):
    # Prioriza las letras sobre los números en caso de conflicto
    reverse_map = {v: k for k, v in forward_map.items() if not k.isdigit()}
    numbers_map = {v: k for k, v in forward_map.items() if k.isdigit()}
    reverse_map.update(numbers_map) # Los números sobreescriben si hay conflicto, pero la letra ya está
    # Para asegurar que la letra tiene prioridad, hacemos al revés:
    reverse_map = {v: k for k, v in forward_map.items() if k.isdigit()}
    letters_map = {v: k for k, v in forward_map.items() if not k.isdigit()}
    reverse_map.update(letters_map)
    return reverse_map

SPANISH_BRAILLE_TO_TEXT_MAP = _create_reverse_map(SPANISH_GRADE_1_MAP)
CATALAN_BRAILLE_TO_TEXT_MAP = _create_reverse_map(CATALAN_GRADE_1_MAP)
EUSKERA_BRAILLE_TO_TEXT_MAP = _create_reverse_map(EUSKERA_GRADE_1_MAP)
GALICIAN_BRAILLE_TO_TEXT_MAP = _create_reverse_map(GALICIAN_GRADE_1_MAP)

SPANISH_8_DOT_BRAILLE_TO_TEXT_MAP = _create_reverse_map(SPANISH_8_DOT_MAP)
CATALAN_8_DOT_BRAILLE_TO_TEXT_MAP = _create_reverse_map(CATALAN_8_DOT_MAP)
EUSKERA_8_DOT_BRAILLE_TO_TEXT_MAP = _create_reverse_map(EUSKERA_8_DOT_MAP)
GALICIAN_8_DOT_BRAILLE_TO_TEXT_MAP = _create_reverse_map(GALICIAN_8_DOT_MAP)

from error_handler import BrailleConversionError

LANGUAGES = {
    'spanish': {
        6: SPANISH_GRADE_1_MAP,
        8: SPANISH_8_DOT_MAP,
        'reverse': {
            6: SPANISH_BRAILLE_TO_TEXT_MAP,
            8: SPANISH_8_DOT_BRAILLE_TO_TEXT_MAP,
        }
    },
    'catalan': {
        6: CATALAN_GRADE_1_MAP,
        8: CATALAN_8_DOT_MAP,
        'reverse': {
            6: CATALAN_BRAILLE_TO_TEXT_MAP,
            8: CATALAN_8_DOT_BRAILLE_TO_TEXT_MAP,
        }
    },
    'euskera': {
        6: EUSKERA_GRADE_1_MAP,
        8: EUSKERA_8_DOT_MAP,
        'reverse': {
            6: EUSKERA_BRAILLE_TO_TEXT_MAP,
            8: EUSKERA_8_DOT_BRAILLE_TO_TEXT_MAP,
        }
    },
    'galician': {
        6: GALICIAN_GRADE_1_MAP,
        8: GALICIAN_8_DOT_MAP,
        'reverse': {
            6: GALICIAN_BRAILLE_TO_TEXT_MAP,
            8: GALICIAN_8_DOT_BRAILLE_TO_TEXT_MAP,
        }
    }
}

def get_char_map(language='spanish', dots_mode=6):
    lang_maps = LANGUAGES.get(language, LANGUAGES['spanish'])
    return lang_maps.get(dots_mode, lang_maps[6])

def get_reverse_map(language='spanish', dots_mode=6):
    lang_maps = LANGUAGES.get(language, LANGUAGES['spanish'])
    reverse_maps = lang_maps['reverse']
    return reverse_maps.get(dots_mode, reverse_maps[6])

def convert_text_to_braille(plain_text, language='spanish', dots_mode=6):
    try:
        char_map = get_char_map(language, dots_mode)
        
        if language == 'catalan':
            if dots_mode == 8:
                plain_text = plain_text.replace('l·l', CATALAN_8_DOT_MAP.get('l·l', ''))
                plain_text = plain_text.replace('L·L', BRAILLE_CAPITAL_SIGN + CATALAN_8_DOT_MAP.get('l·l', ''))
            else:
                plain_text = plain_text.replace('l·l', CATALAN_GRADE_1_MAP.get('l·l', ''))
                plain_text = plain_text.replace('L·L', BRAILLE_CAPITAL_SIGN + CATALAN_GRADE_1_MAP.get('l·l', ''))

        braille_text = ""
        is_number_mode = False
        for char in plain_text:
            if char.isspace():
                braille_text += char
                is_number_mode = False
                continue

            if 0x2800 <= ord(char) <= 0x28FF:
                braille_text += char
                continue

            if char.isdigit():
                if not is_number_mode:
                    braille_text += BRAILLE_NUMBER_SIGN
                    is_number_mode = True
                braille_text += char_map.get(char, '')
            elif char.isupper():
                is_number_mode = False
                braille_text += BRAILLE_CAPITAL_SIGN
                braille_text += char_map.get(char.lower(), '')
            else:
                is_number_mode = False
                braille_text += char_map.get(char, '')
        return braille_text
    except Exception as e:
        raise BrailleConversionError(f"Error al convertir texto a Braille: {e}")


UNICODE_TO_BRF_MAP = {
    '\u2800': ' ', '\u2801': 'a', '\u2802': ',', '\u2803': 'b', '\u2804': ';', '\u2805': 'k', '\u2806': 'l', '\u2807': 'c', '\u2808': 'i', '\u2809': 'f', '\u280a': ':', '\u280b': 's', '\u280c': 'd', '\u280d': 'm', '\u280e': 'h', '\u280f': 't',
    '\u2810': 'e', '\u2811': 'j', '\u2812': 'p', '\u2813': 'o', '\u2814': 'r', '\u2815': 'g', '\u2816': 'q', '\u2817': 'u', '\u2818': 'n', '\u2819': 'v', '\u281a': 'x', '\u281b': 'z', '\u281c': 'w', '\u281d': 'y',
    '\u2820': '\'', '\u2821': '1', '\u2822': '2', '\u2823': '3', '\u2824': '4', '\u2825': '5', '\u2826': '6', '\u2827': '7', '\u2828': '8', '\u2829': '9', '\u282a': '0', '\u282c': '"', '\u282d': '=', '\u282e': '/',
    '\u2830': '!', '\u2831': '@', '\u2832': '#', '\u2833': '$', '\u2834': '%', '\u2835': '^', '\u2836': '&', '\u2837': '*', '\u2838': '(', '\u2839': ')', '\u283a': '_', '\u283b': '+', '\u283c': '-', '\u283d': '[', '\u283e': ']'
}

BRF_TO_UNICODE_MAP = {v: k for k, v in UNICODE_TO_BRF_MAP.items()}

def convert_braille_to_text(braille_text, language='spanish', dots_mode=6):
    try:
        base_map = get_char_map(language, dots_mode)
        reverse_map = get_reverse_map(language, dots_mode)
        
        letter_map = {v: k for k, v in base_map.items() if not k.isdigit()}
        number_map = {v: k for k, v in base_map.items() if k.isdigit()}

        if dots_mode == "computerized":
            computer_map = {chr(i): UNICODE_TO_BRF_MAP.get(chr(i), '') for i in range(0x2800, 0x28FF)}
            return "".join(computer_map.get(char, '') for char in braille_text)

        plain_text = ""
        i = 0
        is_number_mode = False
        while i < len(braille_text):
            char = braille_text[i]

            if char.isspace():
                plain_text += char
                is_number_mode = False
                i += 1
                continue

            if char == BRAILLE_CAPITAL_SIGN:
                i += 1
                if i < len(braille_text):
                    next_braille_char = braille_text[i]
                    mapped_char = letter_map.get(next_braille_char, '')
                    if mapped_char:
                        plain_text += mapped_char.upper()
                i += 1
                continue

            if char == BRAILLE_NUMBER_SIGN:
                is_number_mode = True
                i += 1
                continue

            if language == 'catalan' and braille_text[i:i+3] == base_map.get('l·l', ''):
                plain_text += 'l·l'
                i += 3
                is_number_mode = False
                continue

            current_map = number_map if is_number_mode else letter_map
            
            mapped_char = current_map.get(char)
            
            if mapped_char is None and is_number_mode:
                is_number_mode = False
                mapped_char = letter_map.get(char, '')
            else:
                mapped_char = mapped_char or ''

            plain_text += mapped_char
            i += 1
            
        return plain_text
    except Exception as e:
        raise BrailleConversionError(f"Error al convertir Braille a texto: {e}")


def convert_brf_to_unicode(brf_text, language='spanish', dots_mode=6):
    try:
        unicode_text = ""
        current_brf_to_unicode_map = BRF_TO_UNICODE_MAP

        for char in brf_text:
            unicode_text += current_brf_to_unicode_map.get(char, char)
        return unicode_text
    except Exception as e:
        raise BrailleConversionError(f"Error al convertir BRF a Unicode: {e}")

def convert_brf_to_text(brf_content, language='spanish', dots_mode=6):
    unicode_braille_content = convert_brf_to_unicode(brf_content, language, dots_mode)
    return convert_braille_to_text(unicode_braille_content, language, dots_mode)

def convert_unicode_to_brf_string(unicode_text, language='spanish', dots_mode=6):
    try:
        brf_string = ""
        current_unicode_to_brf_map = UNICODE_TO_BRF_MAP

        for line in unicode_text.splitlines():
            brf_line = ""
            for char in line:
                if 0x2800 <= ord(char) <= 0x28FF:
                    bitmask = ord(char) - 0x2800
                    six_dot_bitmask = bitmask & 0x3F
                    six_dot_unicode_char = chr(0x2800 + six_dot_bitmask)
                    brf_line += current_unicode_to_brf_map.get(six_dot_unicode_char, ' ')
                else:
                    brf_line += current_unicode_to_brf_map.get(char, char)
            brf_string += brf_line + "\r\n"
        return brf_string
    except Exception as e:
        raise BrailleConversionError(f"Error al convertir Unicode a BRF: {e}")

def detect_braille_dots_mode(braille_text):

    """Detects if the braille text contains 8-dot braille characters."""

    for char in braille_text:

        # Check if any character has dots in position 7 or 8

        # Unicode Braille patterns range from U+2800 to U+28FF

        # Dots 7 and 8 correspond to bit 6 (0x40) and bit 7 (0x80) respectively

        if ord(char) >= 0x2800 and (ord(char) & 0xC0): # 0xC0 is 0b11000000 (dots 7 and 8)

            return 8

    return 6



BRAILLE_INFO = {

    '\u2801': {'char': 'a', 'dots': [1], 'desc': 'Letra a'},

    '\u2803': {'char': 'b', 'dots': [1, 2], 'desc': 'Letra b'},

    '\u2809': {'char': 'c', 'dots': [1, 4], 'desc': 'Letra c'},

    '\u2819': {'char': 'd', 'dots': [1, 4, 5], 'desc': 'Letra d'},

    '\u2811': {'char': 'e', 'dots': [1, 5], 'desc': 'Letra e'},

    '\u280b': {'char': 'f', 'dots': [1, 2, 4], 'desc': 'Letra f'},

    '\u281b': {'char': 'g', 'dots': [1, 2, 4, 5], 'desc': 'Letra g'},

    '\u2813': {'char': 'h', 'dots': [1, 2, 5], 'desc': 'Letra h'},

    '\u280a': {'char': 'i', 'dots': [2, 4], 'desc': 'Letra i'},

    '\u281a': {'char': 'j', 'dots': [2, 4, 5], 'desc': 'Letra j'},

    '\u2805': {'char': 'k', 'dots': [1, 3], 'desc': 'Letra k'},

    '\u2807': {'char': 'l', 'dots': [1, 2, 3], 'desc': 'Letra l'},

    '\u280d': {'char': 'm', 'dots': [1, 3, 4], 'desc': 'Letra m'},

    '\u281d': {'char': 'n', 'dots': [1, 3, 4, 5], 'desc': 'Letra n'},

    '\u2815': {'char': 'o', 'dots': [1, 3, 5], 'desc': 'Letra o'},

    '\u280f': {'char': 'p', 'dots': [1, 2, 3, 4], 'desc': 'Letra p'},

    '\u281f': {'char': 'q', 'dots': [1, 2, 3, 4, 5], 'desc': 'Letra q'},

    '\u2817': {'char': 'r', 'dots': [1, 2, 3, 5], 'desc': 'Letra r'},

    '\u280e': {'char': 's', 'dots': [2, 3, 4], 'desc': 'Letra s'},

    '\u281e': {'char': 't', 'dots': [2, 3, 4, 5], 'desc': 'Letra t'},

    '\u2825': {'char': 'u', 'dots': [1, 3, 6], 'desc': 'Letra u'},

    '\u2827': {'char': 'v', 'dots': [1, 2, 3, 6], 'desc': 'Letra v'},

    '\u283a': {'char': 'w', 'dots': [2, 4, 5, 6], 'desc': 'Letra w'},

    '\u282d': {'char': 'x', 'dots': [1, 3, 4, 6], 'desc': 'Letra x'},

    '\u283d': {'char': 'y', 'dots': [1, 3, 4, 5, 6], 'desc': 'Letra y'},

    '\u2835': {'char': 'z', 'dots': [1, 3, 5, 6], 'desc': 'Letra z'},

    '\u283b': {'char': 'ñ', 'dots': [1, 2, 4, 5, 6], 'desc': 'Letra ñ'},

    '\u2816': {'char': 'á', 'dots': [1, 2, 3, 5, 6], 'desc': 'Letra á'},

    '\u2826': {'char': 'é', 'dots': [2, 3, 4, 6], 'desc': 'Letra é'},

    '\u280c': {'char': 'í', 'dots': [3, 4], 'desc': 'Letra í'},

    '\u282c': {'char': 'ó', 'dots': [3, 4, 6], 'desc': 'Letra ó'},

    '\u2836': {'char': 'ú', 'dots': [2, 3, 4, 5, 6], 'desc': 'Letra ú'},

    '\u283a': {'char': 'ü', 'dots': [2, 4, 5, 6], 'desc': 'Letra ü'},

    '\u2802': {'char': '.', 'dots': [2, 5, 6], 'desc': 'Punto'},

    '\u2802': {'char': ',', 'dots': [2], 'desc': 'Coma'},

    '\u2806': {'char': ';', 'dots': [2, 3], 'desc': 'Punto y coma'},

    '\u2812': {'char': ':', 'dots': [2, 5], 'desc': 'Dos puntos'},

    '\u2826': {'char': '?', 'dots': [2, 3, 4, 6], 'desc': 'Signo de interrogación'},

    '\u2816': {'char': '!', 'dots': [2, 3, 5], 'desc': 'Signo de exclamación'},

    '\u2817': {'char': '(', 'dots': [1, 2, 3, 5, 6], 'desc': 'Paréntesis de apertura'},

    '\u2834': {'char': ')', 'dots': [2, 3, 4, 5, 6], 'desc': 'Paréntesis de cierre'},

    '\u2824': {'char': '-', 'dots': [3, 6], 'desc': 'Guión'},

    '\u2826': {'char': '"', 'dots': [2, 3, 5, 6], 'desc': 'Comillas'},

    '\u2828': {'char': '', 'dots': [4, 6], 'desc': 'Signo de mayúscula'},

    '\u283c': {'char': '', 'dots': [3, 4, 5, 6], 'desc': 'Signo de número'},

}



def get_braille_info(braille_char):

    return BRAILLE_INFO.get(braille_char)

def get_dot_pattern(char, language='spanish', dots_mode=6):
    """Devuelve el patrón de puntos numérico para un carácter de texto dado."""
    char_map = get_char_map(language, dots_mode)
    
    braille_char = char_map.get(char.lower())
    if braille_char:
        return ord(braille_char) - 0x2800
    return 0

def get_char_from_dot_pattern(pattern, language='spanish', dots_mode=6):
    """Devuelve el carácter de texto para un patrón de puntos numérico dado."""
    if pattern == 0:
        return ' '
    
    reverse_map = get_reverse_map(language, dots_mode)

    braille_char = chr(0x2800 + pattern)
    return reverse_map.get(braille_char, '?')
