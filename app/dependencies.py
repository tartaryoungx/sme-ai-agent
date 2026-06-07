from typing import Annotated
import logging
from fastapi import Header , HTTPException , Depends
from jose import JWTError , jwt
from app.config import settings

logger = logging.getLogger(__name__)

async def verify_shop(x_shop_id : Annotated[str | None , Header(alias="X-Shop-Id")] = None):
    if not x_shop_id:
        raise HTTPException(status_code=400 , detail="X-Shop-Id header missing")
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
    except ValueError:
        logger.warning("Authorization header format invalid")
        raise HTTPException(status_code=401 , detail="Invalid authorization header format")
    except JWTError as e:
        logger.warning("JWT validation failed: %s", str(e))
        raise HTTPException(status_code=401 , detail="Invalid or expired token")