import base64
import hashlib
import hmac
import json
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix='/api/auth', tags=['auth'])
class LoginRequest(BaseModel):
    username: str
    password: str

@router.post('/login')
def login(request: LoginRequest):
    if request.username != 'examiner' or request.password != 'satsa123':
        raise HTTPException(status_code=401, detail='Invalid examiner credentials')
    header = {'alg': 'HS256', 'typ': 'JWT'}
    payload = {'sub': request.username, 'role': 'examiner', 'exp': int(time.time()) + 8 * 3600}
    encode = lambda value: base64.urlsafe_b64encode(json.dumps(value, separators=(',', ':')).encode()).decode().rstrip('=')
    unsigned = f'{encode(header)}.{encode(payload)}'
    signature = hmac.new(b'local-demo-secret-change-me', unsigned.encode(), hashlib.sha256).digest()
    return {'access_token': f'{unsigned}.{base64.urlsafe_b64encode(signature).decode().rstrip("=")}', 'token_type': 'bearer', 'user': request.username}
