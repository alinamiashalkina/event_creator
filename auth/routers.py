from fastapi import APIRouter, Depends, HTTPException, status, Cookie, Response
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from auth.auth import (
    check_password,
    get_token_payload, get_token_expire,
    create_access_token, create_refresh_token,
)
from db.db import get_db
from db.models import BlacklistedToken, User

templates = Jinja2Templates(directory="auth/templates")
router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


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

    response = JSONResponse(content={"msg": "Login successful"})

    response.set_cookie(key="access_token", value=access_token,
                        httponly=True, samesite="lax")
    response.set_cookie(key="refresh_token", value=refresh_token,
                        httponly=True, samesite="lax")

    return response


@router.get("/logout", response_class=HTMLResponse)
async def logout_page(request: Request):
    return templates.TemplateResponse("logout.html", {"request": request})


@router.post("/logout")
async def logout(
        response: Response,
        access_token: str = Cookie(None),
        refresh_token: str = Cookie(None),
        db: AsyncSession = Depends(get_db),

):
    if not access_token:
        return {"error": "No access token found"}

    if not refresh_token:
        return {"error": "No refresh token found"}

    expires_at_access = get_token_expire(access_token)
    expires_at_refresh = get_token_expire(refresh_token)

    blacklisted_access_token = BlacklistedToken(token=access_token,
                                                expires_at=expires_at_access)
    db.add(blacklisted_access_token)
    blacklisted_refresh_token = BlacklistedToken(token=refresh_token,
                                                 expires_at=expires_at_refresh)
    db.add(blacklisted_refresh_token)
    await db.commit()

    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def get_new_access_token(
        response: Response,
        refresh_token: str = Cookie(None),
        db: AsyncSession = Depends(get_db)
):
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found in cookies"
        )
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
    response.set_cookie(key="access_token", value=access_token,
                        httponly=True, samesite="lax")

    return {"message": "New access token has been obtained"}
