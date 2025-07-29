# studentbot/utils/file_search.py

import os
import fitz  # PyMuPDF
import docx

MAX_RESULT_LENGTH = 1000  # max characters to return to avoid Telegram overflow

def search_in_documents(query: str) -> str | None:
    """Searches for a query in PDF and Word documents in the assets folder."""

    query = query.strip().lower()
    results = []

    pdf_dir = "studentbot/assets/pdfs"
    docx_dir = "studentbot/assets/docs"

    # Search in PDFs
    if os.path.exists(pdf_dir):
        for filename in os.listdir(pdf_dir):
            if filename.lower().endswith(".pdf"):
                try:
                    doc = fitz.open(os.path.join(pdf_dir, filename))
                    for page in doc:
                        text = page.get_text().lower()
                        if query in text:
                            results.append(f"📄 [PDF] {filename}:\n{text.strip()[:MAX_RESULT_LENGTH]}")
                except Exception as e:
                    print(f"⚠️ Error reading PDF {filename}: {e}")

    # Search in Word files
    if os.path.exists(docx_dir):
        for filename in os.listdir(docx_dir):
            if filename.lower().endswith(".docx"):
                try:
                    path = os.path.join(docx_dir, filename)
                    doc = docx.Document(path)
                    for para in doc.paragraphs:
                        text = para.text.strip().lower()
                        if query in text:
                            results.append(f"📝 [DOCX] {filename}:\n{text[:MAX_RESULT_LENGTH]}")
                except Exception as e:
                    print(f"⚠️ Error reading DOCX {filename}: {e}")

    return "\n\n---\n\n".join(results) if results else None
