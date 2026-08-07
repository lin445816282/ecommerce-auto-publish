'''JWT认证 — token签发、校验、依赖注入'''
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'ecom-jwt-secret-v0.7.0-change-in-prod')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 7

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain, hashed):
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id, username, role):
    payload = {
        'sub': str(user_id), 'username': username, 'role': role,
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        'type': 'access',
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id):
    payload = {
        'sub': str(user_id),
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        'type': 'refresh',
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def require_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail='未提供认证令牌',
                           headers={'WWW-Authenticate': 'Bearer'})
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail='令牌无效或已过期',
                           headers={'WWW-Authenticate': 'Bearer'})
    if payload.get('type') != 'access':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='请使用access token')
    return payload


def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)):
    if credentials is None:
        return None
    return decode_token(credentials.credentials)

print('[Auth] JWT handler ready')
