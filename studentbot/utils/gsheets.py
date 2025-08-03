import logging
import json
import asyncio  # Added import
from typing import List, Any
import gspread
from gspread.exceptions import WorksheetNotFound, APIError
from oauth2client.service_account import ServiceAccountCredentials
from studentbot import config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

class GoogleSheetsClient:
    """Manages Google Sheets API operations for data storage."""
    
    def __init__(self):
        self.client = None
        self.spreadsheet = None
    
    def initialize(self):
        """Initialize Google Sheets client with service account credentials."""
        if not config.GOOGLE_CREDS:
            logger.error("❌ GOOGLE_CREDS is not set")
            raise ValueError("Missing Google Sheets credentials")
        if not config.SPREADSHEET_NAME:
            logger.error("❌ SPREADSHEET_NAME is not set")
            raise ValueError("Missing spreadsheet name")
        
        try:
            creds_info = json.loads(config.GOOGLE_CREDS)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, SCOPES)
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open(config.SPREADSHEET_NAME)
            logger.info(f"✅ Google Sheets client initialized for spreadsheet: {config.SPREADSHEET_NAME}")
        except json.JSONDecodeError:
            logger.error("❌ Invalid GOOGLE_CREDS JSON format")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets client: {str(e)}")
            raise
    
    def get_worksheet(self, sheet_name: str) -> gspread.Worksheet:
        """Get a worksheet by name."""
        if not self.spreadsheet:
            logger.error("❌ Google Sheets client is not initialized")
            raise RuntimeError("Google Sheets client not initialized")
        
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            logger.info(f"✅ Accessed worksheet: {sheet_name}")
            return worksheet
        except WorksheetNotFound:
            logger.error(f"❌ Worksheet '{sheet_name}' not found")
            raise
        except Exception as e:
            logger.error(f"❌ Error accessing worksheet '{sheet_name}': {str(e)}")
            raise
    
    @staticmethod
    def validate_user_data(user_data: List[Any], expected_columns: int) -> None:
        """Validate user data list length and content."""
        if not isinstance(user_data, list):
            raise ValueError("User data must be a list")
        if len(user_data) != expected_columns:
            raise ValueError(f"User data must have exactly {expected_columns} columns")
        if not user_data[0] or not isinstance(user_data[0], (int, str)):
            raise ValueError("First column (user_id) must be a non-empty integer or string")
    
    async def add_user_to_sheet(self, sheet_name: str, user_data: List[Any]) -> None:
        """Add a new row with user data to the specified sheet."""
        try:
            worksheet = self.get_worksheet(sheet_name)
            header = await asyncio.get_event_loop().run_in_executor(None, worksheet.row_values, 1)
            self.validate_user_data(user_data, len(header))
            
            await asyncio.get_event_loop().run_in_executor(
                None, worksheet.append_row, user_data, "RAW"
            )
            logger.info(f"✅ Added user to sheet '{sheet_name}': {user_data[0]}")
        except APIError as e:
            logger.error(f"❌ API error adding user to sheet '{sheet_name}': {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to add user to sheet '{sheet_name}': {str(e)}")
            raise
    
    async def add_consultation_to_sheet(self, sheet_name: str, consultation_data: List[Any]) -> None:
        """Add a new consultation request to the specified sheet."""
        try:
            worksheet = self.get_worksheet(sheet_name)
            header = await asyncio.get_event_loop().run_in_executor(None, worksheet.row_values, 1)
            self.validate_user_data(consultation_data, len(header))
            
            await asyncio.get_event_loop().run_in_executor(
                None, worksheet.append_row, consultation_data, "RAW"
            )
            logger.info(f"✅ Added consultation to sheet '{sheet_name}': {consultation_data[0]}")
        except APIError as e:
            logger.error(f"❌ API error adding consultation to sheet '{sheet_name}': {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to add consultation to sheet '{sheet_name}': {str(e)}")
            raise
    
    async def update_user_in_sheet(self, sheet_name: str, user_id: int, user_data: List[Any]) -> None:
        """Update a row in the specified sheet matching the user_id."""
        try:
            worksheet = self.get_worksheet(sheet_name)
            header = await asyncio.get_event_loop().run_in_executor(None, worksheet.row_values, 1)
            self.validate_user_data(user_data, len(header))
            
            cell = await asyncio.get_event_loop().run_in_executor(
                None, worksheet.find, str(user_id), 1
            )
            if not cell:
                raise ValueError(f"User ID {user_id} not found in sheet '{sheet_name}'")
            
            await asyncio.get_event_loop().run_in_executor(
                None, worksheet.update, f"A{cell.row}", [user_data], "RAW"
            )
            logger.info(f"✅ Updated user {user_id} in sheet '{sheet_name}'")
        except APIError as e:
            logger.error(f"❌ API error updating user {user_id} in sheet '{sheet_name}': {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"❌ Value error updating user {user_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to update user {user_id} in sheet '{sheet_name}': {str(e)}")
            raise
    
    async def delete_user_from_sheet(self, sheet_name: str, user_id: int) -> None:
        """Delete the row in the specified sheet corresponding to the user_id."""
        try:
            worksheet = self.get_worksheet(sheet_name)
            cell = await asyncio.get_event_loop().run_in_executor(
                None, worksheet.find, str(user_id), 1
            )
            if not cell:
                raise ValueError(f"User ID {user_id} not found in sheet '{sheet_name}'")
            
            await asyncio.get_event_loop().run_in_executor(
                None, worksheet.delete_rows, cell.row
            )
            logger.info(f"✅ Deleted user {user_id} from sheet '{sheet_name}'")
        except APIError as e:
            logger.error(f"❌ API error deleting user {user_id} in sheet '{sheet_name}': {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"❌ Value error deleting user {user_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to delete user {user_id} in sheet '{sheet_name}': {str(e)}")
            raise

# Instantiate the client
gsheets_client = GoogleSheetsClient()
