from fastapi import HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from db.models import (
    User,
    Contractor,
    ContractorService,
    PortfolioItem,
    Review,
)


async def get_user_or_404(user_id: int, db: AsyncSession):
    """
    Получает пользователя по ID или вызывает ошибку 404,
    если пользователь не найден.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Contractor not found")
    return user


async def get_contractor_or_404(contractor_id: int, db: AsyncSession):
    """
    Получает подрядчика по ID или вызывает ошибку 404,
    если подрядчик не найден.
    """

    result = await db.execute(
        select(Contractor)
        .where(Contractor.id == contractor_id)
        .join(User)
        .options(joinedload(Contractor.user))
    )

    contractor = result.scalars().first()
    if contractor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contractor not found"
        )
    return contractor


async def get_contractor_service_or_404(contractor_id: int,
                                        service_id: int,
                                        db: AsyncSession):
    """
    Получает услугу подрядчика по ID подрядчика и ID услуги
    или вызывает ошибку 404, если услуга не найдена.
    """
    result = await db.execute(
        select(ContractorService)
        .where(ContractorService.contractor_id == contractor_id)
        .where(ContractorService.id == service_id)
    )
    service = result.scalars().first()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Contractor service not found")
    return service


async def get_portfolio_item_or_404(contractor_id: int,
                                    portfolio_item_id: int,
                                    db: AsyncSession):
    """
    Получает элемент потрфолио по ID и по ID подрядчика
    или вызывает ошибку 404, если элемент потрфолио не найден.
    """
    result = await db.execute(
        select(PortfolioItem)
        .where(PortfolioItem.contractor_id == contractor_id)
        .where(PortfolioItem.id == portfolio_item_id)
    )
    portfolio_item = result.scalars().first()
    if portfolio_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Portfolio item not found")
    return portfolio_item


async def get_review_or_404(contractor_id: int,
                            review_id: int,
                            db: AsyncSession):
    """
    Получает отзыв по ID и по ID подрядчика или вызывает ошибку 404,
    если отзыв не найден.
    """
    result = await db.execute(
        select(Review)
        .where(Review.contractor_id == contractor_id)
        .where(Review.id == review_id)
    )
    review = result.scalars().first()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Review not found")
    return review
