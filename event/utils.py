from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from db.models import EventInvitation


async def get_invitation_or_404(
        invitation_id: int,
        db: AsyncSession,
        sender_id: Optional[int] = None,
        recipient_id: Optional[int] = None,
        event_id: Optional[int] = None,
):
    """
    Получает приглашение по его ID и опционально по ID мероприятия,
    отправителя или получателя.
    Если приглашение не найдено, вызывает ошибку 404.
    """
    query = (
        select(EventInvitation)
        .where(EventInvitation.id == invitation_id)
        .options(
            joinedload(EventInvitation.sender),
            joinedload(EventInvitation.recipient),
            joinedload(EventInvitation.event)
        )
    )

    if sender_id is not None:
        query = query.where(EventInvitation.sender_id == sender_id)
    if recipient_id is not None:
        query = query.where(EventInvitation.recipient_id == recipient_id)
    if event_id is not None:
        query = query.where(EventInvitation.event_id == event_id)

    result = await db.execute(query)
    invitation = result.scalars().first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    return invitation
