from typing import Annotated
import logging
from fastapi import Header , HTTPException , Depends
from jose import JWTError , jwt
from app.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
bearer_scheme = HTTPBearer()

logger = logging.getLogger(__name__)

async def verify_shop(x_shop_id : Annotated[str | None , Header(alias="X-Shop-Id")] = None):
    if not x_shop_id:
        raise HTTPException(status_code=400 , detail="X-Shop-Id header missing")
    return x_shop_id
    
async def verify_jwt_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    x_shop_id: str | None = Header(alias="X-Shop-Id", default=None)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        
        # เช็คว่า shop_id ใน token ตรงกับ header ไหม
        if x_shop_id and payload.get("shop_id") != x_shop_id:
            raise HTTPException(status_code=403, detail="Token does not match shop")
        
        return payload

    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")