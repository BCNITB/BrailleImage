import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]

def authenticate_google_docs():
    """Shows user how to authenticate with Google Docs API.
    The file token.json stores the user's access and refresh tokens, and is
    created automatically when the authorization flow completes for the first
    time.
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def read_google_doc(document_id):
    """Reads content from the specified Google Doc and extracts text."""
    creds = authenticate_google_docs()
    try:
        service = build("docs", "v1", credentials=creds)

        # Retrieve the documents contents from the Docs service.
        document = service.documents().get(documentId=document_id).execute()

        doc_content = document.get("body").get("content")
        text_content = ""
        for element in doc_content:
            if "paragraph" in element:
                for paragraph_element in element.get("paragraph").get("elements"):
                    if "textRun" in paragraph_element:
                        text_content += paragraph_element.get("textRun").get("content")
        return text_content

    except HttpError as err:
        print(f"An error occurred: {err}")
        return None

if __name__ == "__main__":
    # Replace with the actual ID of your Google Doc
    # You can find the Document ID in the URL of your Google Doc:
    # https://docs.google.com/document/d/DOCUMENT_ID/edit
    DOCUMENT_ID = "YOUR_DOCUMENT_ID_HERE"

    if DOCUMENT_ID == "YOUR_DOCUMENT_ID_HERE":
        print("Please replace 'YOUR_DOCUMENT_ID_HERE' with your actual Google Doc ID.")
    else:
        extracted_text = read_google_doc(DOCUMENT_ID)
        if extracted_text:
            print("Extracted Text:")
            print(extracted_text)
