import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

def get_worksheet(sheet_name):
    """Returns the worksheet object."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        os.getenv("GOOGLE_CREDS"), scope
    )
    client = gspread.authorize(creds)
    sheet = client.open(os.getenv("SPREADSHEET_NAME")).worksheet(sheet_name)
    return sheet

def add_user_to_sheet(sheet_name, user_data):
    """Adds a new user to the Google Sheet."""
    worksheet = get_worksheet(sheet_name)
    worksheet.append_row(user_data)

def update_user_in_sheet(sheet_name, user_id, user_data):
    """Updates a user's profile in the Google Sheet."""
    worksheet = get_worksheet(sheet_name)
    cell = worksheet.find(str(user_id))
    worksheet.update(f"A{cell.row}", [user_data])

def delete_user_from_sheet(sheet_name, user_id):
    """Deletes a user's profile from the Google Sheet."""
    worksheet = get_worksheet(sheet_name)
    cell = worksheet.find(str(user_id))
    worksheet.delete_rows(cell.row)
