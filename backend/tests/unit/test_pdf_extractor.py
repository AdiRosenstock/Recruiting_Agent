import pytest

from app.services.resume_parsing.pdf_extractor import PDFTextExtractor


def test_extract_text_returns_nonempty_text(sample_resume_bytes: bytes) -> None:
    result = PDFTextExtractor().extract_text(sample_resume_bytes)

    assert result.extraction_method == "pdfplumber"
    assert "Adi Rosenstock" in result.text
    assert "BLOOMBERG" in result.text
    assert len(result.pages) >= 1


def test_extract_text_raises_on_empty_pdf() -> None:
    # A syntactically-valid single blank-page PDF with no text layer.
    import io

    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(200, 200))
    c.showPage()
    c.save()

    with pytest.raises(ValueError, match="No extractable text"):
        PDFTextExtractor().extract_text(buffer.getvalue())
