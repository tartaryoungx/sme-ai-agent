from fastapi import UploadFile
from pypdf import PdfReader
from io import BytesIO


async def extract_text_from_input(
    file: UploadFile | None = None,
    raw_text: str | None = None,
) -> str:
    """
    รับ input ได้ 3 แบบ:
    - PDF
    - TXT
    - Raw Text เช่น Swagger, FAQ, Product Info, Policy
    แล้วคืน text กลางออกไป
    """

    # 1. Raw Text
    if raw_text and raw_text.strip():
        return clean_text(raw_text)

    # 2. File Upload
    if not file:
        raise ValueError("No input provided")

    filename = file.filename.lower()
    content = await file.read()

    # PDF
    if filename.endswith(".pdf"):
        return clean_text(extract_pdf_text(content))

    # TXT
    if filename.endswith(".txt"):
        return clean_text(content.decode("utf-8", errors="ignore"))

    raise ValueError("Unsupported file type. Only PDF, TXT, or raw_text are supported.")


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return "\n".join(pages)


def clean_text(text: str) -> str:
    """
    เคลียร์ text เบื้องต้นก่อนส่งไป chunk
    """
    text = text.replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]

    return "\n".join(lines)