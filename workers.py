import os
import sys
import traceback
from PySide6.QtCore import QObject, Signal, QRunnable, Slot

import image_processor

class WorkerSignals(QObject):
    '''
    Defines the Signals available from a running worker thread.
    Supported signals are:
    finished
        No data
    error
        `tuple` (exctype, value, traceback.format_exc())
    result
        `object` data returned from processing, anything
    progress
        `int` indicating % progress
    '''
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int, str)


class Worker(QRunnable):
    '''
    Worker thread
    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.
    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for thread).
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @Slot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

class BatchWorker(QObject):
    progress = Signal(int)
    finished = Signal(str)

    def __init__(self, folder_path, settings, output_ext, supported_extensions):
        super().__init__()
        self.folder_path = folder_path
        self.settings = settings
        self.output_ext = output_ext
        self.supported_extensions = supported_extensions
        self._is_running = True

    def run(self):
        image_files = [f for f in os.listdir(self.folder_path) if os.path.splitext(f)[1].lower() in self.supported_extensions]
        total_files = len(image_files)
        processed_count = 0
        errors = []

        for i, filename in enumerate(image_files):
            if not self._is_running: break
            
            try:
                full_path = os.path.join(self.folder_path, filename)
                braille_text = image_processor.convert_image_to_braille(
                    full_path,
                    width=100, # or some other default/configurable width
                    contrast=self.settings['contrast'],
                    brightness=self.settings['brightness'],
                    is_inverted=self.settings['invert'],
                    use_dithering=self.settings['dithering'],
                    use_adaptive_thresholding=self.settings.get('adaptive_thresholding', False)
                )

                output_filename = os.path.splitext(filename)[0] + self.output_ext
                output_path = os.path.join(self.folder_path, output_filename)
                encoding = 'ascii' if self.output_ext == '.brf' else 'utf-8'
                
                if self.output_ext == '.brf':
                    output_data = image_processor.convert_unicode_to_brf_string(braille_text)
                else:
                    output_data = braille_text

                with open(output_path, 'w', encoding=encoding) as f:
                    f.write(output_data)
                
                processed_count += 1
            except Exception as e:
                errors.append(f"{filename}: {e}")

            self.progress.emit(i + 1)

        summary = f"Procesamiento completado.\n{processed_count} de {total_files} imágenes convertidas."
        if errors:
            summary += "\n\nSe encontraron los siguientes errores:\n" + "\n".join(errors)
        self.finished.emit(summary)

    def stop(self):
        self._is_running = False

class BrailleConversionWorker(QRunnable):
    def __init__(self, braille_data):
        super(BrailleConversionWorker, self).__init__()
        self.braille_data = braille_data
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            # For now, just save the braille data to a file.
            # In the future, this could be extended to support different formats.
            output_path = "braille_graph.txt"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(self.braille_data)
            self.signals.result.emit(output_path)
        except Exception as e:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self.signals.finished.emit()
