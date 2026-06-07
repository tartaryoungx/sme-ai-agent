from typing import Annotated
from fastapi import Header , HTTPException , Depends
from jose import JWTError , jwt
from app.config import settings

async def verify_shop(x_shop_id : Annotated[str | None , Header(alias="X-Shop_ID")] = None):
    
    if not x_shop_id:
        raise HTTPException(status_code=400 , detail="X-Shop_ID header missing")
    return x_shop_id

async def verify_jwt_auth(authorization: Annotated[str | None , Header(alias="Authorization")] = None):

    if not authorization:
        raise HTTPException(status_code=401 , detail="Authorization header missing")
    
    try:
        token_type , token = authorization.split()
        if token_type.lower() != "bearer":
            raise HTTPException(status_code=401 , detail="Invalid token type")
        
        payload = jwt.decode(token , settings.JWT_SECRET , algorithms=[settings.ALGORITHM])
        return payload
    except (JWTError , ValueError):
        raise HTTPException(status_code=401 , detail="Invalid token")