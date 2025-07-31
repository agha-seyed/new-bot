import os
import logging
import json
from typing import Optional
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaFileUpload
from studentbot import config

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

class GoogleDriveClient:
    """Manages Google Drive API operations for file uploads."""
    
    def __init__(self):
        self.service = None
    
    def initialize(self):
        """Initialize Google Drive service with service account credentials."""
        if not config.GOOGLE_DRIVE_CREDS:
            logger.error("❌ GOOGLE_DRIVE_CREDS is not set")
            raise ValueError("Missing Google Drive credentials")
        
        try:
            creds_info = json.loads(config.GOOGLE_DRIVE_CREDS)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            self.service = build("drive", "v3", credentials=creds)
            logger.info("✅ Google Drive service initialized")
        except json.JSONDecodeError:
            logger.error("❌ Invalid GOOGLE_DRIVE_CREDS JSON format")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Drive service: {str(e)}")
            raise
    
    @staticmethod
    def validate_file(file_path: str) -> None:
        """Validate file existence, type, and size."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        max_size = 10 * 1024 * 1024  # 10MB
        if os.path.getsize(file_path) > max_size:
            raise ValueError(f"File size exceeds 10MB limit: {file_path}")
        
        allowed_extensions = (".pdf", ".doc", ".docx")
        if not file_path.lower().endswith(allowed_extensions):
            raise ValueError(f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")
    
    async def upload_file(self, file_path: str, user_id: int, original_filename: str) -> Optional[str]:
        """Upload a file to Google Drive and return its file ID."""
        if not self.service:
            logger.error("❌ Google Drive service is not initialized")
            raise RuntimeError("Google Drive service not initialized")
        
        if not config.GOOGLE_DRIVE_UPLOAD_FOLDER_ID:
            logger.error("❌ GOOGLE_DRIVE_UPLOAD_FOLDER_ID is not set")
            raise ValueError("Missing Google Drive folder ID")
        
        try:
            if not isinstance(user_id, int) or user_id <= 0:
                raise ValueError("Invalid user_id: must be a positive integer")
            if not original_filename:
                raise ValueError("Original filename cannot be empty")
            self.validate_file(file_path)
            
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_name = f"{user_id}_{timestamp}_{original_filename}"
            
            file_metadata = {
                "name": file_name,
                "parents": [config.GOOGLE_DRIVE_UPLOAD_FOLDER_ID]
            }
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata, media_body=media, fields="id"
            ).execute()
            file_id = file.get("id")
            logger.info(f"✅ File uploaded to Google Drive: {file_id} (name: {file_name})")
            return file_id
        
        except FileNotFoundError as e:
            logger.error(f"❌ File not found: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"❌ Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to upload file to Google Drive: {str(e)}")
            raise

gdrive_client = GoogleDriveClient()
