from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import tempfile
import os
from app.ai.rag import save_pdf_to_rag
from app.dependencies import verify_jwt_auth

router = APIRouter(prefix="/api/v1/documents", tags=["document"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    shop_id: str = None,
    title: str | None = None,
    auth: dict = Depends(verify_jwt_auth),
):
    # ใช้ shop_id จาก JWT token ถ้าไม่ได้ส่งมา
    resolved_shop_id = shop_id or auth.get("shop_id")
    if not resolved_shop_id:
        raise HTTPException(status_code=400, detail="shop_id is required")

    content = await file.read()

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(content)
        temp_pdf_path = temp_file.name

    try:
        chunks = save_pdf_to_rag(temp_pdf_path, shop_id=resolved_shop_id, title=title, filename=file.filename)
        return {
            "filename": file.filename,
            "chunks": chunks
        }

    finally:
        os.remove(temp_pdf_path)