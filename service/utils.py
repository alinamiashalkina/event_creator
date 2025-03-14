from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Category, Service


async def get_category_or_404(category_id: int, db: AsyncSession):
    """
    Получает категорию по ID или вызывает ошибку 404,
    если категория не найдена.
    """
    result = await db.execute(
        select(Category)
        .where(Category.id == category_id)
    )

    category = result.scalars().first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Category not found")
    return category


async def get_service_or_404(category_id: int,
                             service_id: int,
                             db: AsyncSession):
    """
    Получает услугу по ID услуги и ID категории
    или вызывает ошибку 404, если услуга не найдена.
    """
    result = await db.execute(
        select(Service)
        .where(Service.category_id == category_id)
        .where(Service.id == service_id)
    )
    service = result.scalars().first()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Service item not found")
    return service
