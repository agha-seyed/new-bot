import os
import logging
import json
from typing import Optional
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaFileUpload
from config import config

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

class GoogleDriveClient:
    """Manages Google Drive API operations."""
    
    def __init__(self):
        self.service = None
    
    def initialize(self):
        """Initialize Google Drive service with service account credentials."""
        if not config.GOOGLE_DRIVE_CREDS:
            logger.error("❌ GOOGLE_DRIVE_CREDS is not set in configuration.")
            raise RuntimeError("Missing Google Drive credentials.")
        
        try:
            # Load credentials from JSON string
            creds_info = json.loads(config.GOOGLE_DRIVE_CREDS)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            self.service = build("drive", "v3", credentials=creds)
            logger.info("✅ Google Drive service initialized successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Drive service: {str(e)}")
            raise
    
    def validate_file(self, file_path: str) -> None:
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
            logger.error("❌ Google Drive service is not initialized.")
            raise RuntimeError("Google Drive service not initialized.")
        
        if not config.GOOGLE_DRIVE_UPLOAD_FOLDER_ID:
            logger.error("❌ GOOGLE_DRIVE_UPLOAD_FOLDER_ID is not set.")
            raise RuntimeError("Missing Google Drive folder ID.")
        
        try:
            if not isinstance(user_id, int) or user_id <= 0:
                raise ValueError("Invalid user_id: must be a positive integer.")
            if not original_filename:
                raise ValueError("Original filename cannot be empty.")
            self.validate_file(file_path)
            
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_name = f"{user_id}_{timestamp}_{original_filename}"
            
            file_metadata = {
                "name": file_name,
                "parents": [config.GOOGLE_DRIVE_UPLOAD_FOLDER_ID],
            }
            media = MediaFileUpload(file_path, resumable=True)
            uploaded = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            file_id = uploaded.get("id")
            logger.info(f"✅ File uploaded to Google Drive: {file_id} (name: {file_name})")
            return file_id
        
        except Exception as e:
            logger.error(f"❌ Failed to upload file to Google Drive: {str(e)}")
            raise
    
    def close(self):
        """Close Google Drive service."""
        if self.service:
            logger.info("🛑 Google Drive service closed.")
            self.service = None

gdrive_client = GoogleDriveClient()
