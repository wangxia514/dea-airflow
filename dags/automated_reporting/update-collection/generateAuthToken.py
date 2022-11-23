import jwt
from datetime import datetime, timedelta

api_admin_userid = os.getenv("API_ADMIN_USERID")
jwt_passphrase = os.getenv("JWT_PASSPHRASE")

JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 86400  * 10

payload = {
    'sub': api_admin_userid,
    'iat': datetime.now(),
    'exp': datetime.now() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
}

encoded_jwt = jwt.encode(payload, jwt_passphrase , algorithm='HS256')
encoded_jwt_split = encoded_jwt.split(".")
token  =  encoded_jwt_split[0] + "." + encoded_jwt_split[1]
print(token)