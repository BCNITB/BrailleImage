import cv2
import numpy as np
from numba import jit

# Relative coordinates for dots in a Braille cell (row, col)
DOT_POSITIONS = {
    1: (0, 0), 2: (1, 0), 3: (2, 0), 7: (3, 0),
    4: (0, 1), 5: (1, 1), 6: (2, 1), 8: (3, 1),
}

def apply_color_filters(image, active_color_filters):
    if not active_color_filters or image is None:
        return image

    # Create a black image of the same size as the input
    filtered_image = np.zeros_like(image)

    # Split the image into its B, G, R channels
    b, g, r = cv2.split(image)

    # Apply filters based on active_color_filters
    if 'blue' in active_color_filters:
        filtered_image[:, :, 0] = b  # Set blue channel
    if 'green' in active_color_filters:
        filtered_image[:, :, 1] = g  # Set green channel
    if 'red' in active_color_filters:
        filtered_image[:, :, 2] = r  # Set red channel

    return filtered_image

def convert_braille_to_image(braille_text, dot_size=5, dot_spacing=2, line_spacing=2, background_color=(0,0,0), dot_color=(255,255,255)):
    if not braille_text: return np.zeros((10, 10, 3), dtype=np.uint8) # Return a small black image for empty input

    lines = braille_text.split('\n')
    max_chars_per_line = max(len(line) for line in lines)

    # Calculate cell dimensions
    cell_width = dot_size * 2 + dot_spacing * 3 # 2 dots + 3 spaces
    cell_height = dot_size * 4 + dot_spacing * 5 # 4 dots + 5 spaces (for 8-dot)

    # Calculate image dimensions
    img_width = max_chars_per_line * cell_width
    img_height = len(lines) * cell_height

    # Create a blank image
    img = np.full((img_height, img_width, 3), background_color, dtype=np.uint8)

    current_y = 0
    for line in lines:
        current_x = 0
        for char in line:
            if 0x2800 <= ord(char) <= 0x28FF:
                bitmask = ord(char) - 0x2800
                for dot, (row, col) in DOT_POSITIONS.items():
                    if (bitmask >> (dot - 1)) & 1:
                        # Calculate dot center coordinates
                        center_x = current_x + col * (dot_size + dot_spacing) + dot_size
                        center_y = current_y + row * (dot_size + dot_spacing) + dot_size
                        cv2.circle(img, (center_x, center_y), dot_size, dot_color, -1)
            current_x += cell_width
        current_y += cell_height

    return img

@jit(nopython=True)
def _dither_floyd_steinberg(image):
    h, w = image.shape
    for y in range(h):
        for x in range(w):
            old_pixel = image[y, x]
            new_pixel = 255 if old_pixel > 128 else 0
            image[y, x] = new_pixel
            quant_error = old_pixel - new_pixel
            if x + 1 < w:
                image[y, x + 1] = image[y, x + 1] + quant_error * 7 / 16
            if x - 1 >= 0 and y + 1 < h:
                image[y + 1, x - 1] = image[y + 1, x - 1] + quant_error * 3 / 16
            if y + 1 < h:
                image[y + 1, x] = image[y + 1, x] + quant_error * 5 / 16
            if x + 1 < w and y + 1 < h:
                image[y + 1, x + 1] = image[y + 1, x + 1] + quant_error * 1 / 16
    return image

from error_handler import ImageProcessingError

def convert_image_to_braille(image_data, width, contrast, brightness, is_inverted, use_dithering, dots_mode=8, use_adaptive_thresholding=False):
    try:
        # If image_data is bytes, decode it. If it's already a numpy array, use it directly.
        if isinstance(image_data, bytes):
            np_arr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)
        elif isinstance(image_data, np.ndarray):
            img = image_data
        else:
            raise ImageProcessingError("Tipo de datos de imagen no soportado. Se esperaba bytes o numpy.ndarray.")

        if img is None:
            raise ImageProcessingError("No se pudo decodificar la imagen. El archivo puede estar corrupto o en un formato no soportado.")

        # The image adjustments (brightness, contrast, invert) and noise reduction
        # are now handled in main_window.py before calling this function.
        # This function now focuses on braille conversion after pre-processing.

        h, w = img.shape
        if w == 0 or h == 0:
            raise ImageProcessingError("La imagen cargada no tiene dimensiones válidas (ancho o alto es cero).")

        new_w = width * 2
        new_h = int((new_w * h) / w)
        
        new_h = (new_h // 4) * 4
        new_w = (new_w // 2) * 2
        
        if new_h <= 0 or new_w <= 0:
            raise ImageProcessingError("Las dimensiones calculadas para la conversión a Braille son inválidas (menores o iguales a cero). "
                                       "Intente con un ancho de salida diferente o una imagen más grande.")

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        if use_adaptive_thresholding:
            resized = cv2.adaptiveThreshold(resized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        elif use_dithering:
            resized = _dither_floyd_steinberg(resized.astype(np.float32))
        else:
            _, resized = cv2.threshold(resized, 128, 255, cv2.THRESH_BINARY)

        _, binary_image = cv2.threshold(resized, 128, 1, cv2.THRESH_BINARY)

        if dots_mode == 8:
            weights = np.array([0x01, 0x02, 0x04, 0x40, 0x08, 0x10, 0x20, 0x80]).reshape(4, 2)
        else:
            weights = np.array([0x01, 0x02, 0x04, 0x00, 0x08, 0x10, 0x20, 0x00]).reshape(4, 2)

        rows, cols = binary_image.shape
        braille_rows_count = rows // 4
        braille_cols_count = cols // 2

        if braille_rows_count == 0 or braille_cols_count == 0:
            return "" # Devuelve una cadena vacía si la imagen es demasiado pequeña para un carácter Braille

        blocks = binary_image.reshape(braille_rows_count, 4, braille_cols_count, 2)
        bitmasks = np.sum(blocks.transpose(0, 2, 1, 3) * weights, axis=(2, 3))

        braille_chars_matrix = (bitmasks + 0x2800).astype(np.uint32)

        braille_rows = ["".join(map(chr, row)) for row in braille_chars_matrix]
            
        return "\n".join(braille_rows)

    except cv2.error as e:
        raise ImageProcessingError(f"Error de OpenCV durante el procesamiento de la imagen: {e}. "
                                   "Asegúrese de que la biblioteca OpenCV está instalada correctamente.")
    except Exception as e:
        # Captura cualquier otra excepción inesperada y la relanza como una ImageProcessingError
        raise ImageProcessingError(f"Un error inesperado ocurrió durante la conversión de la imagen: {e}")

def apply_segmentation(image, rect, algorithm_type='grabcut'):
    if image is None:
        return None

    if algorithm_type == 'grabcut':
        # rect is (x, y, w, h) - bounding box
        mask = np.zeros(image.shape[:2], np.uint8)
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)

        # Apply GrabCut
        cv2.grabCut(image, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)

        # Create a binary mask where 2 and 0 are background, 1 and 3 are foreground
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

        # Apply the mask to the image
        segmented_image = image * mask2[:, :, np.newaxis]
        return segmented_image
    else:
        return image # No segmentation applied or unsupported algorithm