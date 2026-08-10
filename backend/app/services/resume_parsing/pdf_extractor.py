"""Deterministic PDF -> text extraction. No LLM involved -- this step exists so the LLM
structuring step always operates on the same, inspectable raw text that also gets stored in
`resumes.raw_text` and used later for evidence verification.
"""

import io
from dataclasses import dataclass

import pdfplumber


@dataclass(frozen=True)
class RawResumeText:
    text: str
    pages: list[str]
    extraction_method: str


class PDFTextExtractor:
    method_name = "pdfplumber"

    def extract_text(self, file_bytes: bytes) -> RawResumeText:
        pages: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")

        text = "\n".join(pages).strip()
        if not text:
            raise ValueError(
                "No extractable text found in this PDF -- it may be a scanned image without a "
                "text layer, which this extractor does not OCR."
            )
        return RawResumeText(text=text, pages=pages, extraction_method=self.method_name)
