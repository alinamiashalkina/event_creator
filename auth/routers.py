from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from auth.auth import (
    oauth2_scheme, check_password,
    get_token_payload, get_token_expire,
    create_access_token, create_refresh_token,
)
from db.models import BlacklistedToken, User
from db.db import get_db

router = APIRouter()


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalars().first()

    if not user or not check_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active. Please wait for admin approval.",
        )

    access_token = create_access_token({"user_id": user.id,
                                        "is_active": user.is_active})
    refresh_token = create_refresh_token({"user_id": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    expires_at = get_token_expire(token)

    blacklisted_token = BlacklistedToken(token=token, expires_at=expires_at)
    db.add(blacklisted_token)
    await db.commit()

    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def get_new_access_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    payload = get_token_payload(refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = create_access_token(
        {
            "user_id": user.id,
            "is_active": user.is_active
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
