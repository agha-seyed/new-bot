import os
import fitz  # PyMuPDF for PDFs
import docx
import smtplib
from bs4 import BeautifulSoup
from email.message import EmailMessage

MAX_RESULT_LENGTH = 1200

def send_email(to_email, subject, body):
    """Sends an email with the given subject and body."""
    try:
        sender = os.getenv("EMAIL_SENDER")
        password = os.getenv("EMAIL_PASSWORD")

        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)

        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def extract_text_from_html(file_path):
    """Extract visible text from an HTML file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            return soup.get_text(separator="\n")
    except Exception as e:
        print(f"⚠️ Error reading HTML {file_path}: {e}")
        return ""


def search_in_documents(query: str, user_email: str = None) -> str | None:
    """Searches for a query in PDFs, DOCX, TXT, and HTML files."""
    query = query.strip().lower()
    results = []

    directories = {
        "PDF": "studentbot/assets/pdfs",
        "Word": "studentbot/assets/docs",
        "Text": "studentbot/assets/texts",
        "HTML": "studentbot/assets/html",
    }

    for file_type, dir_path in directories.items():
        if not os.path.exists(dir_path):
            continue

        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if file_type == "PDF" and filename.endswith(".pdf"):
                try:
                    doc = fitz.open(file_path)
                    for page in doc:
                        text = page.get_text().lower()
                        if query in text:
                            snippet = text[text.find(query):text.find(query)+MAX_RESULT_LENGTH]
                            results.append(f"📄 [{file_type}] {filename}:\n{snippet.strip()}")
                except Exception as e:
                    print(f"⚠️ PDF Error {filename}: {e}")

            elif file_type == "Word" and filename.endswith(".docx"):
                try:
                    doc = docx.Document(file_path)
                    for para in doc.paragraphs:
                        text = para.text.strip().lower()
                        if query in text:
                            results.append(f"📝 [{file_type}] {filename}:\n{text[:MAX_RESULT_LENGTH]}")
                except Exception as e:
                    print(f"⚠️ DOCX Error {filename}: {e}")

            elif file_type == "Text" and filename.endswith(".txt"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if query in line.lower():
                                results.append(f"📜 [{file_type}] {filename}:\n{line.strip()[:MAX_RESULT_LENGTH]}")
                except Exception as e:
                    print(f"⚠️ TXT Error {filename}: {e}")

            elif file_type == "HTML" and filename.endswith(".html"):
                text = extract_text_from_html(file_path).lower()
                if query in text:
                    snippet = text[text.find(query):text.find(query)+MAX_RESULT_LENGTH]
                    results.append(f"🌐 [{file_type}] {filename}:\n{snippet.strip()}")

    if not results:
        return None

    final_result = "\n\n---\n\n".join(results)

    # If email is provided, send it
    if user_email:
        subject = "📘 نتیجه جستجو در اسناد"
        body = final_result[:4000]  # limit to avoid SMTP errors
        send_email(user_email, subject, body)

    return final_result
