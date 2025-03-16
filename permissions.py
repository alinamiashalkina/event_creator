from typing import Optional

from fastapi import Depends, HTTPException, status, Query
from sqlalchemy import desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from auth.auth import get_current_user
from db.db import get_db
from db.models import User, UserRole, Event, Contractor
from user.utils import (
    get_user_or_404,
    get_contractor_or_404,
    get_review_or_404,
)


async def admin_only_permission(
    current_user: User = Depends(get_current_user)
):
    """
    Проверка прав доступа и разрешение только для админов.
    """
    if current_user.role == UserRole.ADMIN:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions")


async def admin_or_self_user_permission(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Проверка прав доступа и разрешение только для админов
    или самого пользоваеля. Возвращает пользовтеля.
    """
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
    """
    Проверка прав доступа и разрешение только для админов или самого
    подрядчика. Возвращает подрядчика.
    """
    contractor = await get_contractor_or_404(contractor_id, db)
    if (
            current_user.role == UserRole.ADMIN
            or contractor.user.id == current_user.id
    ):
        return contractor
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions")


async def admin_or_owner_permission(
        contractor_id: int,
        review_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Проверка прав доступа и разрешение только для админов или автора отзыва.
    Возвращает отзыв.
    """
    review = await get_review_or_404(contractor_id, review_id, db)
    owner_id = review.user_id

    if current_user.role == UserRole.ADMIN or owner_id == current_user.id:
        return review
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions")


async def admin_or_creator_or_organizer_permission(
        event_id: Optional[int] = None,
        current_user: User = Depends(get_current_user),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$"),
        db: AsyncSession = Depends(get_db)
):
    """
    Проверка прав доступа к списку событий или конкретному событию:
    если event_id передан, проверяет права доступа к конкретному событию и
    возвращает его в случае разрешения;
    если event_id не передан, возвращает список событий, к которым у
    пользователя  есть доступ, с учетом сортировки и пагинации.
    """
    if event_id is not None:
        result = await db.execute(
            select(Event)
            .where(Event.id == event_id)
            .options(
                joinedload(Event.user),
                joinedload(Event.organizer),
                joinedload(Event.invitations)
            )
        )
        event = result.scalars().first()

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        if (
                current_user.role == UserRole.ADMIN
                or event.user_id == current_user.id
                or event.organizer_id == current_user.id
        ):
            return event
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    else:
        if current_user.role == UserRole.ADMIN:
            result = await db.execute(select(Event))
            events = result.scalars().all()
        else:

            query = (
                select(Event)
                .where((Event.user_id == current_user.id) |
                       (Event.organizer_id == current_user.id))
                .options(
                    joinedload(Event.user),
                    joinedload(Event.organizer),
                    joinedload(Event.invitations)
                )
            )
            if sort_order == "desc":
                query = query.order_by(desc(Event.created_at))
            else:
                query = query.order_by(asc(Event.created_at))

            query = query.offset(skip).limit(limit)

            result = await db.execute(query)
            events = result.scalars().all()

        return events


async def admin_or_creator_permission(
        event_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Проверка прав доступа к конкретному мероприятию только админа
    или создателя. Возвращает мероприятие.
    """
    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(
            joinedload(Event.user),
            joinedload(Event.organizer),
            joinedload(Event.invitations)
        )
    )
    event = result.scalars().first()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    if (
            current_user.role == UserRole.ADMIN
            or event.user_id == current_user.id
    ):
        return event


async def admin_or_creator_or_organizer_or_invited_permission(
        event_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Проверка прав доступа к деталям события. Возвращает мероприятие
    если пользователь админ, создатель или организатор мероприятия, или
    подрядчик, которому направлено приглашение к участию.
    """

    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(
            joinedload(Event.user),
            joinedload(Event.organizer),
            joinedload(Event.invitations)
        )
    )
    event = result.scalars().first()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if (
            current_user.role == UserRole.ADMIN
            or event.user_id == current_user.id
            or event.organizer_id == current_user.id
    ):
        return event

    if current_user.role == UserRole.CONTRACTOR:
        contractor_result = await db.execute(
            select(Contractor)
            .where(user_id=current_user.id)
        )
        contractor = contractor_result.scalars().first()

        if contractor is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="There is a problem with your account. "
                       "Please contact administrator."
            )

        for invitation in event.invitations:
            if invitation.recipient_id == contractor.id:
                return event

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view this event"
    )
