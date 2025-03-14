from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, asc

from db.db import get_db
from permissions import admin_only_permission

from db.models import Category, Service, Contractor, ContractorService
from service.schemas import (
    CategorySchema, CategoryCreateSchema, CategoryUpdateSchema,
    ServiceSchema, ServiceCreateSchema, ServiceUpdateSchema,
)
from user.schemas import ContractorSchema, PortfolioItemSchema
from service.utils import get_category_or_404, get_service_or_404

router = APIRouter()


@router.get("/service_categories",
            response_model=List[CategorySchema])
async def get_service_categories(
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    query = select(Category)

    if sort_order == "desc":
        query = query.order_by(desc(Category.name))
    else:
        query = query.order_by(asc(Category.name))

    query = query.offset(skip).limit(limit)

    results = await db.execute(query)
    categories = results.scalars().all()

    return categories


@router.post("/service_categories",
             dependencies=[Depends(admin_only_permission)],
             response_model=CategorySchema)
async def create_service_category(contractor_id: int,
                                  category: CategoryCreateSchema,
                                  db: AsyncSession = Depends(get_db)):

    existing_category = await db.execute(
        select(Category)
        .where(Category.name == category.name)
    )
    if existing_category.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Category with this name"
                                   "already exists.")

    new_category = Category(**category.model_dump())

    db.add(new_category)
    await db.commit()

    return new_category


@router.get("/service_categories/{category_id}",
            response_model=CategorySchema)
async def category_detail(category_id: int,
                          db: AsyncSession = Depends(get_db)):

    category = await get_category_or_404(category_id, db)

    return category


@router.patch("/service_categories/{category_id}",
              dependencies=[Depends(admin_only_permission)],
              response_model=CategorySchema)
async def update_category(category_id: int,
                          data: CategoryUpdateSchema,
                          db: AsyncSession = Depends(get_db)):
    category = await get_category_or_404(category_id, db)

    category_update_data = data.model_dump(exclude_unset=True)
    if not category_update_data:
        return category

    for key, value in category_update_data.items():
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)

    return category


@router.delete("/service_categories/{category_id}",
               dependencies=[Depends(admin_only_permission)],
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int,
                          db: AsyncSession = Depends(get_db)):

    category = await get_category_or_404(category_id, db)

    await db.delete(category)
    await db.commit()


@router.get("/service_categories/{category_id}/services",
            response_model=List[ServiceSchema])
async def get_services_list_by_category(
        category_id: int,
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    query = select(Service).where(Service.category_id == category_id)

    if sort_order == "desc":
        query = query.order_by(desc(Service.name))
    else:
        query = query.order_by(asc(Service.name))

    query = query.offset(skip).limit(limit)

    results = await db.execute(query)
    services = results.scalars().all()

    return services


@router.post("/service_categories/{category_id}/services",
             dependencies=[Depends(admin_only_permission)],
             response_model=PortfolioItemSchema)
async def create_service(category_id: int,
                         service: ServiceCreateSchema,
                         db: AsyncSession = Depends(get_db)):
    existing_service = await db.execute(
        select(Service)
        .where(Service.name == service.name)
    )
    if existing_service.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Service with this name"
                                   "already exists.")

    new_service = Service(
        category_id=category_id,
        **service.model_dump()
    )

    db.add(new_service)
    await db.commit()

    return new_service


@router.get("/service_categories/{category_id}/services/{service_id}",
            response_model=ServiceSchema)
async def service_detail(category_id: int,
                         service_id: int,
                         db: AsyncSession = Depends(get_db)):

    service = await get_service_or_404(category_id, service_id, db)

    return service


@router.patch(
    "/service_categories/{category_id}/services/{service_id}",
    dependencies=[Depends(admin_only_permission)],
    response_model=ServiceSchema
)
async def update_service(category_id: int,
                         service_id: int,
                         data: ServiceUpdateSchema,
                         db: AsyncSession = Depends(get_db)):
    service = await get_service_or_404(category_id, service_id, db)

    service_update_data = data.model_dump(exclude_unset=True)
    if not service_update_data:
        return service

    for key, value in service_update_data.items():
        setattr(service, key, value)

    await db.commit()
    await db.refresh(service)

    return service


@router.delete(
    "/service_categories/{category_id}/services/{service_id}",
    dependencies=[Depends(admin_only_permission)],
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_service(category_id: int,
                         service_id: int,
                         db: AsyncSession = Depends(get_db)):

    service = await get_service_or_404(category_id, service_id, db)

    await db.delete(service)
    await db.commit()


@router.get(
    "/service_categories/{category_id}/services/{service_id}/contractors",
    response_model=List[ContractorSchema])
async def get_contractors_by_service(
        category_id: int,
        service_id: int,
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    """
    Получение списка подрядчиков, оказывающих выбранную услугу.
    Сортировка по рейтингу. Доступно всем зарегистрированным пользователям.
    """
    query = (
        select(Contractor)
        .join(ContractorService)
        .join(Service)
        .join(Category)
        .where(Service.id == service_id)
    )
    if sort_order == "desc":
        query = query.order_by(desc(Contractor.average_rating))
    else:
        query = query.order_by(asc(Contractor.average_rating))

    query = query.offset(skip).limit(limit)

    results = await db.execute(query)
    contractors = results.scalars().all()

    if not contractors:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No contractors found for the specified "
                                   "service in this category")
    return contractors
