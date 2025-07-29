import os
import logging

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_gdrive_service():
    """
    Creates and returns an authorized Google Drive service instance.
    Requires a 'token.json' for access tokens and a 'GOOGLE_DRIVE_CREDS' env variable pointing to client_secrets.json.
    """
    creds = None
    token_path = "token.json"
    secrets_path = os.getenv("GOOGLE_DRIVE_CREDS")

    if not secrets_path or not os.path.exists(secrets_path):
        logger.error("GOOGLE_DRIVE_CREDS not set or file does not exist.")
        raise RuntimeError("Missing Google credentials.")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def upload_file(file_path: str, user_id: int, original_filename: str) -> str:
    """
    Uploads a file to a Google Drive folder defined in GOOGLE_DRIVE_UPLOAD_FOLDER_ID.
    Returns the file ID of the uploaded file.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"{file_path} not found.")

    folder_id = os.getenv("GOOGLE_DRIVE_UPLOAD_FOLDER_ID")
    if not folder_id:
        logger.error("GOOGLE_DRIVE_UPLOAD_FOLDER_ID environment variable not set.")
        raise RuntimeError("Missing Google Drive folder ID.")

    try:
        service = get_gdrive_service()
        file_metadata = {
            "name": f"{user_id}_{original_filename}",
            "parents": [folder_id],
        }
        media = MediaFileUpload(file_path)
        uploaded = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        logger.info(f"File uploaded to Google Drive: {uploaded.get('id')}")
        return uploaded.get("id")

    except Exception as e:
        logger.exception(f"Failed to upload file to Google Drive: {e}")
        raise
