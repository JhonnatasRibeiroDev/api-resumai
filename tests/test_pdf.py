from pathlib import Path

import fitz

from app.utils.pdf import extract_text_from_pdf


def create_pdf(path: Path, text: str) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_extract_text_from_pdf(tmp_path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path, "Conteúdo acadêmico para resumir.")

    assert "Conteúdo acadêmico" in extract_text_from_pdf(pdf_path)
