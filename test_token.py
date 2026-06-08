from jose import jwt
from app.config import settings
import time

SECRET_KEY = settings.JWT_SECRET

payload = {
    "sub": "user123",
    "exp": int(time.time()) + 3600
}

token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print("Generated JWT Token:", token)
print("Bearer " + token)

