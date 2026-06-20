from fastapi import APIRouter, UploadFile, File, Depends
import tempfile
import os
from app.ai.rag import save_pdf_to_rag
from app.dependencies import verify_jwt_auth

router = APIRouter(prefix="/documents", tags=["document"])

@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    shop_id: str = None,
    title: str | None = None,
    auth: dict = Depends(verify_jwt_auth),
):
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