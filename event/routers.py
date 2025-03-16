from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    BackgroundTasks,
)
from sqlalchemy import desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.db import get_db
from db.models import (
    Event,
    User,
    Contractor,
    EventInvitation,
    EventInvitationStatus,
)
from event.schemas import (
    EventOutSchema,
    EventCreateSchema,
    EventUpdateSchema,
    EventOrganizerUpdateSchema,
    EventInvitationOutSchema,
    EventInvitationCreateSchema,
)
from event.utils import get_invitation_or_404
from mail.mail import send_email
from permissions import (
    admin_or_creator_or_organizer_permission,
    admin_or_self_user_permission,
    admin_or_creator_permission,
    admin_or_self_contractor_permission,
    admin_or_creator_or_organizer_or_invited_permission,
)
from user.utils import get_contractor_or_404

router = APIRouter()


@router.get("/events", response_model=List[EventOutSchema])
async def get_events(
        skip: int = Query(0, ge=0),
        imit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$"),
        events: List[Event] = Depends(admin_or_creator_or_organizer_permission)
):
    """
    Получение списка мероприятий. Админ получает список всех мероприятий,
    пользователь - список созданных им и где он выступает организатором.
    """
    return events


@router.get("/events/{event_id}", response_model=EventOutSchema)
async def event_detail(
        event_id: int,
        event: Event = Depends(
            admin_or_creator_or_organizer_or_invited_permission)
):
    """
    Получение деталей мероприятия. Доступно для админов, создателя и
    организатора мероприятия, а также подрядчиков, получивших приглашение
    к участию в мероприятии.
    """
    return event


@router.post("/users/{user_id}/events", response_model=EventOutSchema)
async def create_event(
        user_id: int,
        event: EventCreateSchema,
        user: User = Depends(admin_or_self_user_permission),
        db: AsyncSession = Depends(get_db)
):
    """
    Создание мероприятия на странице пользователя. При создании мероприятия
    организатором назначается создатель.
    Доступно для админов и для самого пользователя.
    """
    new_event = Event(
        user_id=user.id,
        organizer_id=user.id,
        name=event.name,
        description=event.description,
        location=event.location,
        start_time=event.start_time,
        end_time=event.end_time
    )
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    return new_event


@router.patch(
    "/users/{user_id}/events/{event_id}",
    response_model=EventOutSchema
)
async def update_event(
        event_id: int,
        event_data: EventUpdateSchema,
        user_id: int,
        event: Event = Depends(admin_or_creator_or_organizer_permission),
        db: AsyncSession = Depends(get_db)
):
    """
    Обновление мероприятия на странице пользователя.
    Доступно для админов и для самого пользователя.
    """
    update_event_data = event_data.model_dump(exclude_unset=True)

    if not update_event_data:
        return event

    for key, value in update_event_data.items():
        setattr(event, key, value)
    await db.commit()
    await db.refresh(event)
    return event


@router.patch(
    "/users/{user_id}/events/{event_id}/organizer",
    response_model=EventOutSchema
)
async def update_event_organizer(
    event_id: int,
    organizer_data: EventOrganizerUpdateSchema,
    user_id: int,
    event: Event = Depends(admin_or_creator_or_organizer_permission),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление организатора мероприятия. Организатором может быть назначен
    только подрядчик, который получил и принял приглашение на мероприятие
    и был подтвержден отправителем.
    Доступно только для создателя мероприятия (он же дефолтный организатор)
    или админа.
    """

    contractor = await get_contractor_or_404(organizer_data.organizer_id, db)

    result = await db.execute(
        select(EventInvitation)
        .where(
            (EventInvitation.event_id == event_id) &
            (EventInvitation.recipient_id == contractor.id) &
            (EventInvitation.status == EventInvitationStatus.CONFIRMED)
        )
    )
    invitation = result.scalars().first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contractor must have a confirmed invitation to the event"
        )

    event.organizer_id = contractor.id
    await db.commit()
    await db.refresh(event)

    return event


@router.delete("/users/{user_id}/events/{event_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
        event_id: int,
        user_id: int,
        background_tasks: BackgroundTasks,
        event: Event = Depends(admin_or_creator_permission),
        db: AsyncSession = Depends(get_db)
):
    """
    Удаление мероприятия на странице пользователя.
    Доступно только для админа и  создателя мероприятия.
    """
    result = await db.execute(
        select(EventInvitation)
        .where(EventInvitation.event_id == event_id)
    )
    invitations = result.scalars().all()

    await db.delete(event)
    await db.commit()

    for invitation in invitations:
        background_tasks.add_task(
            send_email,
            to=invitation.recipient.user.email,
            subject="Мероприятие отменено",
            template_name="event_deleted.html",
            context={"event_name": event.name,
                     "user_name": event.user.name}
        )

    return {"message": "Event deleted successfully"}


@router.post("/users/{user_id}/events/{event_id}/invites",
             response_model=EventInvitationOutSchema)
async def invite_contractor(
        event_id: int,
        background_tasks: BackgroundTasks,
        data: EventInvitationCreateSchema,
        user_id: int,
        event: Event = Depends(admin_or_creator_or_organizer_permission),
        db: AsyncSession = Depends(get_db)
):
    """
    Отправка подрядчику приглашения к участию в мероприятии.
    Доступно админам, создателю мероприятия и организатору.
    """
    contractor = await get_contractor_or_404(data.recipient_id, db)

    result = await db.execute(
        select(EventInvitation)
        .where(
            (EventInvitation.event_id == event.id) &
            (EventInvitation.recipient_id == contractor.id)
        )
    )
    existing_invitation = result.scalars().first()
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contractor already invited to this event"
        )

    new_invitation = EventInvitation(
        event_id=event.id,
        sender_id=user_id,
        recipient_id=contractor.id,
        status=EventInvitationStatus.PENDING
    )
    db.add(new_invitation)
    await db.commit()

    invitation = await get_invitation_or_404(new_invitation.id, db)

    background_tasks.add_task(
        send_email,
        to=contractor.user.email,
        subject="Новое приглашение на мероприятие",
        template_name="invitation_sent.html",
        context={"event_name": event.name,
                 "user_name": invitation.sender.name,
                 "invitation_id": invitation.id}
    )
    return invitation


@router.get("/users/{user_id}/events/{event_id}/invites",
            response_model=List[EventInvitationOutSchema])
async def get_sent_event_invitations(
        event_id: int,
        user_id: int,
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$"),
        event: Event = Depends(admin_or_creator_or_organizer_permission),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение списка приглашений к участию в мероприятии, направленных
    подрядчикам. Доступно админам, создателю мероприятия и организатору.
    """
    query = (
        select(EventInvitation)
        .where(EventInvitation.event_id == event.id)
    )
    if sort_order == "desc":
        query = query.order_by(desc(EventInvitation.created_at))
    else:
        query = query.order_by(asc(EventInvitation.created_at))

    query = query.offset(skip).limit(limit)

    results = await db.execute(query)
    invitations = results.scalars().all()

    return invitations


@router.get("/contractors/{contractor_id}/invites",
            response_model=List[EventInvitationOutSchema])
async def get_received_invitations(
        contractor_id: int,
        contractor: Contractor = Depends(admin_or_self_contractor_permission),
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    """
    Получение списка поступивших подрядчику приглашений к участию
    в мероприятиях. Доступно админам и самому подрядчику.
    """
    query = (
        select(EventInvitation)
        .where(EventInvitation.recipient_id == contractor.id)
    )

    if sort_order == "desc":
        query = query.order_by(desc(EventInvitation.created_at))
    else:
        query = query.order_by(asc(EventInvitation.created_at))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    invitations = result.scalars().all()

    return invitations


@router.patch(
    "/contractors/{contractor_id}/invitations/{invitation_id}",
    response_model=EventInvitationOutSchema)
async def accept_or_decline_invitation(
        contractor_id: int,
        invitation_id: int,
        background_tasks: BackgroundTasks,
        contractor: Contractor = Depends(admin_or_self_contractor_permission),
        action: str = Query(..., description="Action to perform: "
                                             "'accept' or 'decline'"),
        db: AsyncSession = Depends(get_db)
):
    """
    Принятие или отклонение приглашения на участие в мероприятии.
    Доступно только для админа и самого подрядчика.
    """

    invitation = await get_invitation_or_404(invitation_id=invitation_id,
                                             recipient_id=contractor.id,
                                             db=db)

    if action == "accept":
        invitation.status = EventInvitationStatus.ACCEPTED
    elif action == "decline":
        invitation.status = EventInvitationStatus.DECLINED
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use 'accept' or 'decline'."
        )

    await db.commit()

    db_invitation = await get_invitation_or_404(invitation.id, db)

    background_tasks.add_task(
        send_email,
        to=db_invitation.sender.email,
        subject="Статус приглашения изменен",
        template_name="invitation_status_updated.html",
        context={"contractor_name": contractor.user.name,
                 "status": invitation.status}
    )

    return invitation


@router.patch(
    "/users/{user_id}/events/{event_id}/invitations/{invitation_id}",
    response_model=EventInvitationOutSchema)
async def confirm_or_cancel_invitation(
        user_id: int,
        event_id: int,
        invitation_id: int,
        background_tasks: BackgroundTasks,
        action: str = Query(..., description="Action to perform: "
                                             "'confirm' or 'cancel'"),
        event: Event = Depends(admin_or_creator_or_organizer_permission),
        db: AsyncSession = Depends(get_db)
):
    """
    Подтверждение или отмена приглашения на участие в мероприятии.
    Доступно только для админа, создателя мероприятия или организатора.
    Подтвердить можно только приглашение, которое уже принято подрядчиком.
    """

    invitation = await get_invitation_or_404(invitation_id=invitation_id,
                                             sender_id=user_id,
                                             event_id=event.id,
                                             db=db)
    recipient = await get_contractor_or_404(invitation.recipient_id, db)

    if (
            action == "confirm"
            and invitation.status != EventInvitationStatus.ACCEPTED
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot confirm an invitation that is not accepted "
                   "by the contractor"
        )

    if action == "confirm":
        invitation.status = EventInvitationStatus.CONFIRMED
        await db.commit()

        invitation = await get_invitation_or_404(invitation_id=invitation.id,
                                                 db=db)
        background_tasks.add_task(
            send_email,
            to=recipient.user.email,
            subject="Участие подтверждено",
            template_name="invitation_confirmed.html",
            context={"user_name": recipient.user.name,
                     "event_name": invitation.event.name}
        )
        return invitation

    elif action == "cancel":
        background_tasks.add_task(
            send_email,
            to=recipient.user.email,
            subject="Приглашение отменено",
            template_name="invitation_canceled.html",
            context={"user_name": recipient.user.name,
                     "event_name": invitation.event.name}
        )

        await db.delete(invitation)
        await db.commit()
        return {"message": "Invitation canceled successfully"}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use 'confirm' or 'cancel'."
        )
