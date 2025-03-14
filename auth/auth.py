import os
from datetime import datetime, timedelta, timezone

import bcrypt
from dotenv import load_dotenv
from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.responses import JSONResponse

from db.db import get_db
from db.models import BlacklistedToken, User

load_dotenv()

JWT_SECRET = os.environ["SECRET_KEY"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(hours=1)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(data: dict) -> str:
    payload = {
        "user_id": data["user_id"],
        "is_active": data["is_active"],
        "exp": datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE,
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    payload = {
        "user_id": data["user_id"],
        "exp": datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRE,
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def verify_token(token: str, db: AsyncSession) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=JWT_ALGORITHM)
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        print(f"JWTError: {str(e)}")
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if user is None:
        raise credentials_exception

    return user


def get_token_payload(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return payload


def get_token_expire(token):
    payload = get_token_payload(token)
    expires_at = datetime.fromtimestamp(payload["exp"], timezone.utc)
    return expires_at


def get_current_user(request: Request):
    user = request.state.user
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


async def auth_middleware(request: Request, call_next):
    """
    Middleware для проверки токена и статуса пользователя.
    """

    public_endpoints = [
        "/register/user", "/register/contractor", "/login", "/refresh"
    ]
    if request.url.path in public_endpoints:
        return await call_next(request)

    try:
        token = await oauth2_scheme(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code,
                            content={"detail": e.detail})

    async for db in get_db():
        result = await db.execute(
            select(BlacklistedToken).where(BlacklistedToken.token == token))
        if result.scalars().first():
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token is blacklisted"},
            )
        user = await verify_token(token, db)

        if not user.is_active:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Account is not active. "
                                   "Please wait for admin approval."},
            )

        request.state.user = user

    return await call_next(request)
