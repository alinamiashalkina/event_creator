from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    BackgroundTasks,
)
from sqlalchemy import desc, asc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from auth.auth import hash_password, get_current_user
from db.db import get_db
from mail.mail import send_email
from permissions import (
    admin_only_permission,
    admin_or_self_contractor_permission,
    admin_or_self_user_permission,
    admin_or_owner_permission,
)
from db.models import (
    User,
    UserRole,
    Contractor,
    ContractorService,
    PortfolioItem,
    Review,
)
from user.schemas import (
    UserRegistrationSchema, UserOutSchema, UserUpdateSchema,
    ContractorRegistrationSchema, ContractorApplicationSchema,
    ContractorOutSchema, ContractorApplicationListSchema,
    ContractorUpdateSchema,
    ContractorServiceSchema, ContractorServiceListSchema,
    ContractorServiceUpdateSchema, ContractorServiceCreateSchema,
    PortfolioItemSchema, PortfolioItemUpdateSchema,
    ReviewListSchema, ReviewCreateSchema, ReviewSchema, ContractorSchema,
    PortfolioItemAddSchema,
)
from user.utils import (
    get_review_or_404,
    get_portfolio_item_or_404,
    get_contractor_service_or_404, get_contractor_or_404,
)

router = APIRouter()


@router.post("/register/admin",
             dependencies=[Depends(admin_only_permission)])
async def register_admin(user: UserRegistrationSchema,
                         db: AsyncSession = Depends(get_db)):
    """
    Зарегистрировать админа может только другой админ.
    Первый админ - superuser, создается в базе данных вручную.
    """

    existing_user = await db.execute(
        select(User).where(
            (User.username == user.username) | (User.email == user.email))
    )
    if existing_user.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User with this username or email "
                                   "already exists.")

    hashed_password = hash_password(user.password)

    new_admin = User(username=user.username,
                     email=user.email,
                     password_hash=hashed_password,
                     name=user.name,
                     contact_data=user.contact_data,
                     role=UserRole.ADMIN,
                     is_active=True)
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)

    return {"msg": "Admin registered successfully", "user_id": new_admin.id}


@router.post("/register/user")
async def register_user(user: UserRegistrationSchema,
                        db: AsyncSession = Depends(get_db)):
    """
    Регистрация пользователя.
    """

    existing_user = await db.execute(
        select(User).where(
            (User.username == user.username) | (User.email == user.email))
    )
    if existing_user.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User with this username or email "
                                   "already exists.")

    hashed_password = hash_password(user.password)

    new_user = User(username=user.username,
                    email=user.email,
                    password_hash=hashed_password,
                    name=user.name,
                    contact_data=user.contact_data,
                    role=UserRole.USER,
                    is_active=True)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"msg": "User registered successfully", "user_id": new_user.id}


@router.get("/users",
            dependencies=[Depends(admin_only_permission)],
            response_model=List[UserOutSchema])
async def get_users(
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    """
    Получение списка пользователей (заказчиков).
    Сортировка по дате последнего обновления. Доступно только админам.
    """
    query = select(User).where(User.role == UserRole.USER)
    if sort_order == "desc":
        query = query.order_by(desc(User.updated_at))
    else:
        query = query.order_by(asc(User.updated_at))
    query = query.offset(skip).limit(limit)

    results = await db.execute(query)
    users = results.scalars().all()
    return users


@router.get("/users/{user_id}", response_model=UserOutSchema)
async def user_detail(user_id: int,
                      user: User = Depends(admin_or_self_user_permission)):
    """
    Получение деталей конкретного пользователя.
    Доступно только админам и самому пользователю.
    """
    return user


@router.patch("/users/{user_id}", response_model=UserOutSchema)
async def update_user(user_id: int,
                      user_update: UserUpdateSchema,
                      user: User = Depends(admin_or_self_user_permission),
                      db: AsyncSession = Depends(get_db)
                      ):
    """
    Обновление данных пользователя (заказчика).
    Доступно только админам и самому пользователю.
    """
    update_data = user_update.model_dump(exclude_unset=True)
    if not update_data:
        return user

    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/users/{user_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int,
                      user: User = Depends(admin_or_self_user_permission),
                      db: AsyncSession = Depends(get_db)):
    """
    Удаление пользователя.
    Доступно только админам и самому пользователю.
    """

    await db.delete(user)
    await db.commit()


@router.post("/register/contractor")
async def register_contractor(contractor: ContractorRegistrationSchema,
                              db: AsyncSession = Depends(get_db)):
    """
    Регистрация подрядчика. Создаются записи в таблицах users и contractor,
    contractor_service и если переданы элементы портфолио - записи в таблице
    portfolio_item.
    До подтверждения регистрации админом пользователь неактивен,
    статус подрядчика - не подтвержден.
    """
    username = contractor.user.username
    email = contractor.user.email

    existing_user = await db.execute(
        select(User).where(
            (User.username == username) | (User.email == email))
    )
    if existing_user.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User with this username or email "
                                   "already exists.")

    hashed_password = hash_password(contractor.user.password)
    new_user = User(
        username=username,
        email=email,
        password_hash=hashed_password,
        name=contractor.user.name,
        contact_data=contractor.user.contact_data,
        role=UserRole.CONTRACTOR,
        is_active=False
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    new_contractor = Contractor(
        user_id=new_user.id,
        photo=contractor.photo,
        description=contractor.description,
        is_approved=False
    )
    db.add(new_contractor)
    await db.commit()
    await db.refresh(new_contractor)

    for service in contractor.services:
        new_contractor_service = ContractorService(
            service_id=service.service_id,
            contractor_id=new_contractor.id,
            description=service.description,
            price=service.price
        )
        db.add(new_contractor_service)
        await db.commit()
        await db.refresh(new_contractor_service)

    if contractor.portfolio_items:
        for item in contractor.portfolio_items:
            new_item = PortfolioItem(
                contractor_id=new_contractor.id,
                type=item.type,
                url=item.url,
                description=item.description
            )
            db.add(new_item)
            await db.commit()
            await db.refresh(new_item)

    return {"msg": "Contractor registration submitted successfully",
            "contractor_id": new_contractor.id}


@router.get("/contractor_applications",
            dependencies=[Depends(admin_only_permission)],
            response_model=List[ContractorApplicationListSchema])
async def get_contractor_applications(
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    """
    Получение списка заявок на регистрацию подрядчиков.
    Сортировка по дате добавления подрядчика. Доступно только админам.
    """
    query = (
        select(Contractor)
        .join(User)
        .where(Contractor.is_approved.is_(False))
        .options(joinedload(Contractor.user))
    )
    if sort_order == "desc":
        query = query.order_by(desc(Contractor.created_at))
    else:
        query = query.order_by(asc(Contractor.created_at))
    query = query.offset(skip).limit(limit)

    results = await db.execute(query)
    contractor_applications = results.scalars().all()

    return contractor_applications


@router.get("/contractor_applications/{contractor_id}",
            dependencies=[Depends(admin_only_permission)],
            response_model=ContractorApplicationSchema)
async def contractor_application_detail(contractor_id: int,
                                        db: AsyncSession = Depends(get_db)):
    """
    Получение деталей заявки на регистрацию подрядчика.
    Доступно только админам.
    """
    result = await db.execute(
        select(Contractor)
        .join(User)
        .where(Contractor.id == contractor_id)
        .options(
            joinedload(Contractor.user),
            joinedload(Contractor.services),
            joinedload(Contractor.portfolio_items))
    )

    application = result.scalars().first()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Contractor not found")

    return application


@router.post(
    "/contractor_applications/{contractor_id}/approve_contractor",
    dependencies=[Depends(admin_only_permission)]
)
async def approve_contractor(contractor_id: int,
                             background_tasks: BackgroundTasks,
                             db: AsyncSession = Depends(get_db)):
    """
    Одобрение регистрации подрядчика. Статус пользователя изменяется
    на активный, статус подрядчика изменяется на "подтвержден".
    Доступно только админам.
    """
    contractor = await get_contractor_or_404(contractor_id, db)
    contractor.user.is_active = True
    contractor.is_approved = True
    await db.commit()

    background_tasks.add_task(
        send_email,
        to=contractor.user.email,
        subject="Ваша заявка одобрена",
        template_name="approval_email.html",
        context={"name": contractor.user.name}
    )

    return {"msg": "Contractor approved successfully"}


@router.post(
    "/contractor_applications/{contractor_id}/reject_contractor",
    dependencies=[Depends(admin_only_permission)]
)
async def reject_contractor(contractor_id: int,
                            background_tasks: BackgroundTasks,
                            db: AsyncSession = Depends(get_db)):
    """
    Отклонение регистрации подрядчика. Удаляется запись в таблице users,
    запись в таблице contractor, а также связанные записи в других таблицах,
    удалятся в соответствии с настройками каскадного удаления.
    Доступно только админам.
    """
    contractor = await get_contractor_or_404(contractor_id, db)

    background_tasks.add_task(
        send_email,
        to=contractor.user.email,
        subject="Ваша заявка отклонена",
        template_name="rejection_email.html",
        context={"name": contractor.user.name}
    )
    await db.delete(contractor.user)
    await db.commit()

    return {"msg": "Contractor rejected and user record deleted"}


@router.get("/contractors", response_model=List[ContractorSchema])
async def get_contractors(
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    """
    Получение списка подрядчиков. Сортировка по имени.
    Доступно всем зарегистрированным пльзователям.
    """
    query = (
        select(Contractor)
        .join(User)
        .where(User.role == UserRole.CONTRACTOR)
        .options(joinedload(Contractor.user))
    )
    if sort_order == "desc":
        query = query.order_by(desc(User.name))
    else:
        query = query.order_by(asc(User.name))
    query = query.offset(skip).limit(limit)

    results = await db.execute(query)
    contractors = results.scalars().all()
    return contractors


@router.get("/contractors/{contractor_id}",
            response_model=ContractorOutSchema)
async def contractor_detail(contractor_id: int,
                            db: AsyncSession = Depends(get_db)):
    """
    Получение деталей о подрядчике.
    Доступно всем зарегистрированным пльзователям.
    """
    contractor = await get_contractor_or_404(contractor_id, db)
    return contractor


@router.patch("/contractors/{contractor_id}",
              response_model=ContractorOutSchema)
async def update_contractor(contractor_id: int,
                            data: ContractorUpdateSchema,
                            contractor: Contractor = Depends(
                                admin_or_self_contractor_permission),
                            db: AsyncSession = Depends(get_db)
                            ):
    """
    Обновление данных подрядчика и связанного пользователя.
    Доступно только админам и самому подрядчику.
    """

    contractor_update_data = data.model_dump(exclude_unset=True)
    if not contractor_update_data:
        return contractor

    user_update_data = contractor_update_data.pop("user", None)

    for key, value in contractor_update_data.items():
        setattr(contractor, key, value)

    if user_update_data:
        for user_key, user_value in user_update_data.items():
            setattr(contractor.user, user_key, user_value)

    await db.commit()
    await db.refresh(contractor)

    return contractor


@router.delete("/contractors/{contractor_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_contractor(
        contractor_id: int,
        contractor: Contractor = Depends(admin_or_self_contractor_permission),
        db: AsyncSession = Depends(get_db)):
    """
    Удаление подрядчика и связанного пользователя.
    Доступно только админам и самому подрядчику.
    """

    await db.delete(contractor)
    await db.delete(contractor.user)
    await db.commit()


@router.get("/contractors/{contractor_id}/services",
            response_model=List[ContractorServiceListSchema])
async def get_contractor_services(contractor_id: int,
                              db: AsyncSession = Depends(get_db)):
    """
    Получение списка услуг конкретного подрядчика.
    Доступно всем зарегистрированным пользователям.
    """
    results = await db.execute(
        select(ContractorService)
        .where(ContractorService.contractor_id == contractor_id)
    )
    services = results.scalars().all()

    return services


@router.post("/contractors/{contractor_id}/services",
             response_model=ContractorServiceSchema)
async def create_contractor_service(
        contractor_id: int,
        data: ContractorServiceCreateSchema,
        contractor: Contractor = Depends(admin_or_self_contractor_permission),
        db: AsyncSession = Depends(get_db)
):
    """
    Создание услуги конкретного подрядчика.
    Доступно админам и самому подрядчику.
    """
    new_service = ContractorService(
        contractor_id=contractor.id,
        **data.model_dump()
    )

    db.add(new_service)
    await db.commit()

    return new_service


@router.get("/contractors/{contractor_id}/services/{service_id}",
            response_model=ContractorServiceSchema)
async def contractor_service_detail(contractor_id: int,
                                    service_id: int,
                                    db: AsyncSession = Depends(get_db)):
    """
    Получение деталей услуги подрядчика.
    Доступно всем зарегистрированным пользователям.
    """
    service = await get_contractor_service_or_404(
        contractor_id, service_id, db
    )

    return service


@router.patch("/contractors/{contractor_id}/services/{service_id}",
              response_model=ContractorServiceSchema)
async def update_contractor_service(
        contractor_id: int,
        service_id: int,
        data: ContractorServiceUpdateSchema,
        contractor: Contractor = Depends(admin_or_self_contractor_permission),
        db: AsyncSession = Depends(get_db)
):
    """
    Обновление данных об услуге  подрядчика.
    Доступно админам и самому подрядчику.
    """
    service = await get_contractor_service_or_404(
        contractor.id, service_id, db
    )

    service_update_data = data.model_dump(exclude_unset=True)
    if not service_update_data:
        return service

    for key, value in service_update_data.items():
        setattr(service, key, value)

    await db.commit()
    await db.refresh(service)

    return service


@router.delete("/contractors/{contractor_id}/services/{service_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_contractor_service(contractor_id: int,
                                    service_id: int,
                                    contractor: Contractor = Depends(
                                        admin_or_self_contractor_permission),
                                    db: AsyncSession = Depends(get_db)):
    """
    Удаление услуги подрядчика.
    Доступно админам и самому подрядчику.
    """
    service = await get_contractor_service_or_404(
        contractor.id, service_id, db
    )

    await db.delete(service)
    await db.commit()


@router.get("/contractors/{contractor_id}/portfolio",
            response_model=List[PortfolioItemSchema])
async def get_contractor_portfolio(
        contractor_id: int,
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    """
    Получение всего портфолио подрядчика.
    Сортировка эелемнтов портфолио по дате последнего обновления.
    Доступно всем зарегистрированным пользователям.
    """
    query = (
        select(PortfolioItem)
        .where(PortfolioItem.contractor_id == contractor_id)
    )
    if sort_order == "desc":
        query = query.order_by(desc(PortfolioItem.updated_at))
    else:
        query = query.order_by(asc(PortfolioItem.updated_at))
    query = query.offset(skip).limit(limit)

    results = await db.execute(query)
    portfolio = results.scalars().all()

    return portfolio


@router.post("/contractors/{contractor_id}/portfolio",
             response_model=PortfolioItemAddSchema)
async def create_portfolio_item(
        contractor_id: int,
        data: PortfolioItemSchema,
        contractor: Contractor = Depends(admin_or_self_contractor_permission),
        db: AsyncSession = Depends(get_db)
):
    """
    Создание элемента портфолио подрядчика.
    Доступно админам и самому подрядчику.
    """
    new_portfolio_item = PortfolioItem(
        contractor_id=contractor.id,
        **data.model_dump()
    )

    db.add(new_portfolio_item)
    await db.commit()

    return new_portfolio_item


@router.get("/contractors/{contractor_id}/portfolio/{portfolio_item_id}",
            response_model=PortfolioItemSchema)
async def portfolio_item_detail(contractor_id: int,
                                portfolio_item_id: int,
                                db: AsyncSession = Depends(get_db)):
    """
    Получение деталей элемента портфолио подрядчика.
    Доступно всем зарегистрированным пользователям.
    """
    portfolio_item = await get_portfolio_item_or_404(
        contractor_id, portfolio_item_id, db
    )

    return portfolio_item


@router.patch(
    "/contractors/{contractor_id}/portfolio/{portfolio_item_id}",
    response_model=PortfolioItemSchema
)
async def update_portfolio_item(
        contractor_id: int,
        portfolio_item_id: int,
        data: PortfolioItemUpdateSchema,
        contractor: Contractor = Depends(admin_or_self_contractor_permission),
        db: AsyncSession = Depends(get_db)
):
    """
    Обновление элемента портфолио подрядчика.
    Доступно админам и самому подрядчику.
    """
    portfolio_item = await get_portfolio_item_or_404(
        contractor.id, portfolio_item_id, db
    )

    portfolio_item_update_data = data.model_dump(exclude_unset=True)
    if not portfolio_item_update_data:
        return portfolio_item

    for key, value in portfolio_item_update_data.items():
        setattr(portfolio_item, key, value)

    await db.commit()
    await db.refresh(portfolio_item)

    return portfolio_item


@router.delete(
    "/contractors/{contractor_id}/portfolio/{portfolio_item_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_portfolio_item(contractor_id: int,
                                portfolio_item_id: int,
                                contractor: Contractor = Depends(
                                    admin_or_self_contractor_permission),
                                db: AsyncSession = Depends(get_db)):
    """
    Удаление элемента портфолио подрядчика.
    Доступно админам и самому подрядчику.
    """
    portfolio_item = await get_portfolio_item_or_404(
        contractor.id, portfolio_item_id, db
    )

    await db.delete(portfolio_item)
    await db.commit()


@router.get("/contractors/{contractor_id}/reviews",
            response_model=List[ReviewListSchema])
async def get_reviews_of_contractor(
        contractor_id: int,
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    """
    Получение списка отзывов на подрядчика. Сортировка по дате добавления.
    Доступно всем зарегистрированным пользователям.
    """
    query = (
        select(Review)
        .where(Review.contractor_id == contractor_id)
    )
    if sort_order == "desc":
        query = query.order_by(desc(Review.created_at))
    else:
        query = query.order_by(asc(Review.created_at))
    query = query.offset(skip).limit(limit)

    results = await db.execute(query)
    reviews = results.scalars().all()

    return reviews


@router.post("/contractors/{contractor_id}/reviews",
             response_model=ReviewSchema)
async def create_review(
        contractor_id: int,
        data: ReviewCreateSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Создание отзыва и обновление рейтинга подрядчика.
    Доступно всем зарегистрированным пользователям.
    """
    new_review = Review(
        contractor_id=contractor_id,
        user_id=current_user.id,
        **data.model_dump()
    )

    db.add(new_review)
    await db.commit()

    reviews_query = await db.execute(
        select(Review)
        .where(Review.contractor_id == contractor_id)
    )
    reviews = reviews_query.scalars().all()

    total_ratings = sum(review.rating for review in reviews)
    average_rating = total_ratings / len(reviews) if reviews else None

    await db.execute(
        update(Contractor)
        .where(Contractor.id == contractor_id)
        .values(average_rating=average_rating)
    )
    await db.commit()

    return new_review


@router.get("/contractors/{contractor_id}/reviews/{review_id}",
            response_model=ReviewSchema)
async def review_detail(contractor_id: int,
                        review_id: int,
                        db: AsyncSession = Depends(get_db)):
    """
    Просмотр отзыва. Доступно всем зарегистрированным пользователям.
    """

    review = await get_review_or_404(contractor_id, review_id, db)

    return review


@router.delete(
    "/contractors/{contractor_id}/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_review(contractor_id: int,
                        review_id: int,
                        review: Review = Depends(admin_or_owner_permission),
                        db: AsyncSession = Depends(get_db)):
    """
    Удаление отзыва и обновление рейтинга подрядчика.
    Доступно админам и автору отзыва.
    """
    await db.delete(review)
    await db.commit()

    reviews_query = await db.execute(
        select(Review)
        .where(Review.contractor_id == contractor_id)
    )
    reviews = reviews_query.scalars().all()

    total_ratings = sum(review.rating for review in reviews)
    average_rating = total_ratings / len(reviews) if reviews else None

    await db.execute(
        update(Contractor)
        .where(Contractor.id == contractor_id)
        .values(average_rating=average_rating)
    )
    await db.commit()
