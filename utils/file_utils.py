import os
import fitz  # PyMuPDF
import docx  # python-docx

def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    # Use get_text() if available, else fallback to getText()
    # This handles different versions of pymupdf
    text = ""
    for page in doc:
        if hasattr(page, "get_text"):  # Modern method
            text += page.get_text()
        else:  # Older versions fallback
            text += page.getText()
    return text

def extract_text_from_docx(docx_path: str) -> str:
    doc = docx.Document(docx_path)
    return "\n".join(para.text for para in doc.paragraphs)

def extract_texts_from_folder(folder_path: str, file_extensions=['.pdf', '.docx']) -> str:
    all_text = ""
    for filename in os.listdir(folder_path):
        if any(filename.lower().endswith(ext) for ext in file_extensions):
            full_path = os.path.join(folder_path, filename)
            try:
                if filename.lower().endswith('.pdf'):
                    text = extract_text_from_pdf(full_path)
                elif filename.lower().endswith('.docx'):
                    text = extract_text_from_docx(full_path)
                else:
                    continue
                all_text += f"\n\n=== Document: {filename} ===\n\n{text}"
            except Exception as e:
                print(f"Warning: Failed to load {filename}: {e}")
    return all_text
