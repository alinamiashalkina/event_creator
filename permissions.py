from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.auth import get_current_user
from db.db import get_db
from db.models import User, UserRole
from user.utils import (
    get_user_or_404,
    get_contractor_or_404,
    get_review_or_404,
)


async def admin_only_permission(
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.ADMIN:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions")


async def admin_or_self_user_permission(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    user = await get_user_or_404(user_id, db)
    if current_user.role == UserRole.ADMIN or user.id == current_user.id:
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions")


async def admin_or_self_contractor_permission(
        contractor_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    contractor = await get_contractor_or_404(contractor_id, db)
    user_id = contractor.user_id
    user = await get_user_or_404(user_id, db)
    if current_user.role == UserRole.ADMIN or user.id == current_user.id:
        return contractor
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions")


async def admin_or_owner_permission(
        contractor_id: int,
        review_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    review = await get_review_or_404(contractor_id, review_id, db)
    owner_id = review.user_id

    if current_user.role == UserRole.ADMIN or owner_id == current_user.id:
        return review
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions")
