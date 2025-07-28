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
-   **Arrival Guide:** A comprehensive arrival guide for students, covering topics such as airport entry, reaching Perugia, getting a Codice Fiscale, opening a bank account, getting health insurance, university registration, and finding housing.
-   **ISEE Calculation:** A feature to help students determine their financial aid eligibility.
-   **Scholarship Status:** A feature to inform students of their scholarship eligibility based on their ISEE.
-   **Gamification:** A points system and a leaderboard to encourage user engagement.
-   **News Feed:** A feature to provide students with the latest news and deadlines from relevant sources.
-   **Consultation System:** A system that allows users to ask for advice from the bot's administrators.
-   **Document Submission:** A system that allows users to upload documents to the bot.
-   **Weather:** A feature to provide students with up-to-date information about the weather in Perugia.
-   **Cost of Living:** A feature to provide students with up-to-date information about the cost of living in Italy.
-   **Search:** A feature that allows users to search for information within the bot.
-   **AI Integration:** AI integration to provide more intelligent and human-like responses to user queries.
-   **UI/UX Improvements:** The bot has been designed with a focus on user experience.

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
    -   `ADMIN_CHAT_ID`: The chat ID of the admin.
    -   `OPENWEATHERMAP_API_KEY`: Your OpenWeatherMap API key.
    -   `EXCHANGE_RATE_API_KEY`: Your ExchangeRate-API key.
    -   `REDIS_URL`: The URL of your Redis database.
    -   `HUGGINGFACE_API_KEY`: Your Hugging Face API key.
    -   `OPENAI_API_KEY`: Your OpenAI API key.
    -   `WEBHOOK_SECRET`: Your webhook secret.
    -   `BASE_URL`: The base URL of your bot.
    -   `PORT`: The port to run the bot on.
    -   `PYTHON_VERSION`: The Python version to use.
    -   `QUESTIONS_SHEET_NAME`: The name of the Google Sheet for questions.
    -   `SHEET_ID`: The ID of your Google Sheet.
    - `GOOGLE_DRIVE_CREDS`: The path to your Google Drive API credentials file.
    - `GOOGLE_DRIVE_UPLOAD_FOLDER_ID`: The ID of the folder to upload files to.
4.  **Run the bot:**
    ```
    python -m studentbot.main
    ```

## Deployment

The bot is designed to be deployed to Render. To deploy the bot to Render, you will need to:

1.  Create a new web service on Render.
2.  Connect your GitHub repository to the web service.
3.  Set the environment variables in the Render dashboard.
4.  Set the start command to `python -m studentbot.main`.

## Commands

-   `/start`: Starts the bot.
-   `/help`: Displays the help message.
-   `/menu`: Displays the main menu.
-   `/profile`: Displays the user's profile.
-   `/register`: Starts the registration process.
-   `/edit_profile`: Starts the edit profile process.
-   `/delete_profile`: Deletes the user's profile.
-   `/isee`: Starts the ISEE calculation process.
-   `/points`: Displays the user's points.
-   `/leaderboard`: Displays the leaderboard.
-   `/news`: Displays the latest news.
-   `/consult`: Starts the consultation process.
-   `/consult_status`: Displays the status of the user's consultation requests.
-   `/upload_document`: Starts the document submission process.
-   `/weather`: Displays the weather in Perugia.
-   `/cost`: Starts the cost of living calculation process.
-   `/search`: Starts the search process.
-   `/ask`: Asks a question to the bot.
-   `/tts`: Converts text to speech.
-   `/contact`: Displays the contact us message.
-   `/about`: Displays the about us message.
-   `/arrival_guide`: Displays the arrival guide menu.
-   `/admin_consultations`: Displays all consultation requests to the admin.
-   `/reply`: Replies to a consultation request.
-   `/archive`: Archives a consultation request.
-   `/view_file`: Views the file for a consultation request.
-   `/question`: Starts the question submission process.
-   `/feedback`: Sends a feedback form.
-   `/migration_status`: Displays the user's migration status.
-   `/update_migration_status`: Updates the user's migration status.
