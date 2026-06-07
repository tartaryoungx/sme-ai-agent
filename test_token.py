from jose import jwt
import time

SECRET_KEY = "XB2HK+Q7tMV+79IO0ZXwGe+640VXyzAJsZfuKeVMpuCCSHaRdQmQW1maxNhsDiniPTyw/bt/tx12W7btut3o8Q=="

payload = {
    "sub": "user123",
    "exp": int(time.time()) + 3600
}

token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print("Generated JWT Token:", token)
print("Baerer " + token)

