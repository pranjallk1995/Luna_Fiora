"""Turn a statement file into text, and that text into pieces the model can read."""
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

class StatementLocked(ValueError):
    """A password-protected PDF, opened with no password or the wrong one."""

def statement_text(data,mime_type,password=None):
    if mime_type!="application/pdf":
        try: return data.decode("utf-8-sig")
        except UnicodeDecodeError: return data.decode("latin-1")
    try: document=pdfium.PdfDocument(data,password=password)
    except pdfium.PdfiumError as error:
        if getattr(error,"err_code",None)==pdfium_c.FPDF_ERR_PASSWORD:
            raise StatementLocked("This PDF is locked. Import the folder again with its password.") from error
        raise ValueError("This is not a valid PDF.") from error
    try: return "\n".join(page.get_textpage().get_text_bounded() for page in document)
    finally: document.close()

def statement_chunks(text,mime_type,size):
    """Pieces of whole lines up to size characters; a CSV's header starts each piece."""
    lines=[line for line in text.splitlines() if line.strip()]
    header=lines.pop(0)+"\n" if mime_type!="application/pdf" and mime_type!="text/plain" and lines else ""
    chunks,current=[],""
    for line in lines:
        if current and len(current)+len(line)>=size: chunks.append(header+current); current=""
        current+=line[:size]+"\n"
    if current: chunks.append(header+current)
    return chunks
