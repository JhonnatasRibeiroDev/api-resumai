from pathlib import Path


class PDFExtractionError(Exception):
    pass


def extract_text_from_pdf(path: str | Path) -> str:
    try:
        import fitz

        with fitz.open(path) as document:
            text_parts = [page.get_text("text") for page in document]
    except Exception as exc:
        raise PDFExtractionError("PDF inválido ou ilegível.") from exc

    text = "\n".join(part.strip() for part in text_parts if part and part.strip()).strip()
    if not text:
        raise PDFExtractionError("PDF sem texto extraível.")
    return text
