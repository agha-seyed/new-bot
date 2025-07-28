import os
import PyMuPDF
import docx

def search_in_documents(query):
    """Searches for a query in the documents."""
    for filename in os.listdir("studentbot/assets/pdfs"):
        if filename.endswith(".pdf"):
            doc = PyMuPDF.open(f"studentbot/assets/pdfs/{filename}")
            for page in doc:
                text = page.get_text()
                if query in text:
                    return text
    for filename in os.listdir("studentbot/assets/docs"):
        if filename.endswith(".docx"):
            doc = docx.Document(f"studentbot/assets/docs/{filename}")
            for para in doc.paragraphs:
                if query in para.text:
                    return para.text
    return None
