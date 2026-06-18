from fastapi import APIRouter, UploadFile, File
import tempfile
import os
from app.ai.rag import save_pdf_to_rag

router = APIRouter(prefix="/documents", tags=["document"])

@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...), shop_id: str | None = "b5c79bc0-8e1b-46a7-a1d7-229b53f971de", title: str | None = None):
    content = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(content)
        temp_pdf_path = temp_file.name

    try:
        chunks = save_pdf_to_rag(temp_pdf_path, shop_id=shop_id, title=title, filename=file.filename)
        print("successfully added!")
        return {
            "filename": file.filename,
            "chunks": chunks
        }

    finally:
        os.remove(temp_pdf_path)