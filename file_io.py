import os
import os
import docx
import PyPDF2
from striprtf.striprtf import rtf_to_text
from PySide6.QtWidgets import QMessageBox, QInputDialog

# Imports para Google API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Si modificas estos SCOPES, elimina el archivo token.json.
SCOPES = ['https://www.googleapis.com/auth/documents.readonly']

def get_google_credentials():
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    raise FileProcessingError(f"No se pudo refrescar el token de Google: {e}. Por favor, autoriza de nuevo.")
            else:
                script_dir = os.path.dirname(os.path.realpath(__file__))
                creds_path = os.path.join(script_dir, 'credentials.json')
                if not os.path.exists(creds_path):
                    raise FileProcessingError("El archivo 'credentials.json' de Google no se encuentra. "
                                            "Descárgalo desde Google Cloud Console y colócalo en el directorio de la aplicación.")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds
    except Exception as e:
        raise FileProcessingError(f"Error de autenticación con Google: {e}")

def read_structural_elements(elements):
    try:
        text = ''
        for value in elements:
            if 'paragraph' in value:
                elements_in_paragraph = value.get('paragraph').get('elements')
                for elem in elements_in_paragraph:
                    text += elem.get('textRun', {}).get('content', '')
            elif 'table' in value:
                table = value.get('table')
                for row in table.get('tableRows'):
                    for cell in row.get('tableCells'):
                        text += read_structural_elements(cell.get('content'))
                    text += '\n'
        return text
    except Exception as e:
        raise FileProcessingError(f"Error al leer los elementos estructurales del documento de Google: {e}")

from error_handler import FileProcessingError

def extract_text_from_rtf(file_path):
    try:
        with open(file_path, 'r') as f:
            rtf_content = f.read()
        return rtf_to_text(rtf_content)
    except (FileNotFoundError, IOError) as e:
        raise FileProcessingError(f"Error al procesar el archivo RTF '{os.path.basename(file_path)}': {e}")

def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise FileProcessingError(f"Error al procesar el archivo DOCX '{os.path.basename(file_path)}': {e}")

def extract_text_from_pdf(file_path):
    try:
        text = ""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                if (extracted := page.extract_text()):
                    text += extracted + '\n'
        return text
    except Exception as e:
        raise FileProcessingError(f"Error al procesar el archivo PDF '{os.path.basename(file_path)}': {e}")

def extract_text_from_odt(file_path):
    try:
        import ezodf
        doc = ezodf.opendoc(file_path)
        text = ""
        for p in doc.body:
            if isinstance(p, ezodf.paragraph.Paragraph):
                text += p.plaintext() + '\n'
        return text
    except Exception as e:
        raise FileProcessingError(f"Error al procesar el archivo ODT '{os.path.basename(file_path)}': {e}")
