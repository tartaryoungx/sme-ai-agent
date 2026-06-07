from jose import jwt
import time

SECRET_KEY = "test_secret_key"

payload = {
    "sub": "user123",
    "exp": int(time.time()) + 3600
}

token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print("Generated JWT Token:", token)
print("Baerer " + token)
