import os
import gspread
import logging
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)

# Google Sheets API Scopes
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def get_worksheet(sheet_name: str):
    """
    Connects to the Google Spreadsheet and returns the worksheet by name.
    Raises error if credentials or sheet not found.
    """
    creds_path = os.getenv("GOOGLE_CREDS")
    spreadsheet_name = os.getenv("SPREADSHEET_NAME")

    if not creds_path or not os.path.exists(creds_path):
        logger.error("GOOGLE_CREDS path not found.")
        raise FileNotFoundError("Google credentials file is missing.")

    if not spreadsheet_name:
        logger.error("SPREADSHEET_NAME not set.")
        raise RuntimeError("Spreadsheet name not specified in environment.")

    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, SCOPES)
        client = gspread.authorize(creds)
        worksheet = client.open(spreadsheet_name).worksheet(sheet_name)
        return worksheet
    except Exception as e:
        logger.exception(f"Error accessing worksheet '{sheet_name}': {e}")
        raise

def add_user_to_sheet(sheet_name: str, user_data: list):
    """
    Adds a new row with user data to the sheet.
    """
    try:
        worksheet = get_worksheet(sheet_name)
        worksheet.append_row(user_data)
        logger.info(f"User added to sheet '{sheet_name}': {user_data}")
    except Exception as e:
        logger.exception(f"Failed to add user to sheet: {e}")

def update_user_in_sheet(sheet_name: str, user_id: int, user_data: list):
    """
    Updates a row in the sheet matching the user_id (assumed in column A).
    """
    try:
        worksheet = get_worksheet(sheet_name)
        cell = worksheet.find(str(user_id))
        worksheet.update(f"A{cell.row}", [user_data])
        logger.info(f"User {user_id} updated in sheet '{sheet_name}'.")
    except Exception as e:
        logger.exception(f"Failed to update user {user_id} in sheet: {e}")

def delete_user_from_sheet(sheet_name: str, user_id: int):
    """
    Deletes the row in the sheet corresponding to the user_id (in column A).
    """
    try:
        worksheet = get_worksheet(sheet_name)
        cell = worksheet.find(str(user_id))
        worksheet.delete_rows(cell.row)
        logger.info(f"User {user_id} deleted from sheet '{sheet_name}'.")
    except Exception as e:
        logger.exception(f"Failed to delete user {user_id} from sheet: {e}")
