# Student Helper Bot

This is a Telegram bot designed to help international students, with a focus on students in Perugia, Italy.

## Features

-   **Multi-language support:** The bot can communicate in English, Italian, and Persian.
-   **User Profiles:** Users can create and manage their profiles, including their name, age, email, country, and field of study.
-   **Database Integration:** User data is stored in a PostgreSQL database.
-   **Google Sheets Integration:** User data is also backed up to a Google Sheet.
-   **Menu System:** A menu system provides access to all of the bot's features.
-   **Input Validation:** The bot validates user input to ensure that it is in the correct format.
-   **Error Handling:** The bot provides helpful error messages to the user if they enter invalid data.

## Setup

1.  **Clone the repository:**
    ```
    git clone https://github.com/your-username/student-helper-bot.git
    ```
2.  **Install the dependencies:**
    ```
    pip install -r requirements.txt
    ```
3.  **Set up the environment variables:**
    -   `TELEGRAM_TOKEN`: Your Telegram bot token.
    -   `DATABASE_URL`: The URL of your PostgreSQL database.
    -   `GOOGLE_CREDS`: The path to your Google API credentials file.
    -   `SPREADSHEET_NAME`: The name of your Google Sheet.
4.  **Run the bot:**
    ```
    python -m studentbot.main
    ```

## Database Schema

The `users` table has the following schema:

| Column         | Type        | Description               |
| -------------- | ----------- | ------------------------- |
| id             | BIGINT      | The user's Telegram ID.   |
| first_name     | VARCHAR(255) | The user's first name.    |
| last_name      | VARCHAR(255) | The user's last name.     |
| age            | INTEGER     | The user's age.           |
| email          | VARCHAR(255) | The user's email address. |
| country        | VARCHAR(255) | The user's country.       |
| field_of_study | VARCHAR(255) | The user's field of study. |
| created_at     | TIMESTAMP   | The timestamp of creation. |

## Google Sheets API Setup

1.  Follow the instructions in the [gspread documentation](https://docs.gspread.org/en/latest/oauth2.html) to create a service account and get a credentials file.
2.  Share your Google Sheet with the service account's email address.
3.  Set the `GOOGLE_CREDS` environment variable to the path of your credentials file.
4.  Set the `SPREADSHEET_NAME` environment variable to the name of your Google Sheet.
