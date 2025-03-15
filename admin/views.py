from sqladmin import ModelView

from db.db import AsyncSessionLocal
from db.models import (
    User,
    UserRole,
    Contractor,
    Service,
    PortfolioItem,
    Review,
    Category,
    ContractorService,
    BlacklistedToken,
)


class BlacklistedTokenAdmin(ModelView, model=BlacklistedToken):
    column_list = [
        BlacklistedToken.id,
        BlacklistedToken.token,
        BlacklistedToken.expires_at
    ]
    can_delete = True
    column_searchable_list = [
        BlacklistedToken.id,
        BlacklistedToken.token,
        BlacklistedToken.expires_at
    ]
    column_sortable_list = [
        BlacklistedToken.id,
        BlacklistedToken.expires_at
    ]


class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.username,
        User.email,
        User.name,
        User.role,
        User.is_active,
        User.created_at,
        User.updated_at,
    ]
    column_searchable_list = [User.username, User.email, User.name]
    column_sortable_list = [User.id, User.username, User.created_at]

    form_excluded_columns = [
        User.created_at,
        User.updated_at,
    ]
    form_choices = {
        "role": [
            (UserRole.ADMIN, "Admin"),
            (UserRole.CONTRACTOR, "Contractor"),
            (UserRole.USER, "User"),
        ]
    }

    column_details_list = [
        User.username,
        User.email,
        User.name,
        User.role,
        User.is_active,
        User.contractor,
        User.reviews,
    ]


class ContractorAdmin(ModelView, model=Contractor):
    column_list = [
        Contractor.id,
        Contractor.user_id,
        Contractor.photo,
        Contractor.description,
        Contractor.is_approved,
        Contractor.average_rating,
        Contractor.created_at,
        Contractor.updated_at,
    ]
    column_searchable_list = [
        Contractor.description,
        Contractor.user_id,
    ]
    column_sortable_list = [
        Contractor.id,
        Contractor.user_id,
        Contractor.created_at
    ]
    form_columns = [
        Contractor.user_id,
        Contractor.photo,
        Contractor.description,
        Contractor.is_approved,
        "services",
        "portfolio_items",
    ]
    column_details_list = [
        Contractor.user_id,
        Contractor.user,
        Contractor.photo,
        Contractor.description,
        Contractor.is_approved,
        Contractor.average_rating,
        Contractor.services,
        Contractor.portfolio_items,
        Contractor.reviews,
    ]

    async def create_model(self, request, data):
        user_data = data.pop("user", {})
        services_data = data.pop("services", [])
        portfolio_data = data.pop("portfolio_items", [])

        async with AsyncSessionLocal() as db:
            try:
                user = User(**user_data)
                db.add(user)
                await db.commit()

                contractor = Contractor(user_id=user.id, **data)
                db.add(contractor)
                await db.commit()

                for service_data in services_data:
                    service = ContractorService(contractor_id=contractor.id,
                                                **service_data)
                    db.add(service)

                for item_data in portfolio_data:
                    item = PortfolioItem(contractor_id=contractor.id,
                                         **item_data)
                    db.add(item)

                await db.commit()
            except Exception as e:
                await db.rollback()
                raise e


class ContractorServiceAdmin(ModelView, model=ContractorService):
    column_list = [
        ContractorService.id,
        ContractorService.service_id,
        ContractorService.contractor_id,
        ContractorService.description,
        ContractorService.price,
    ]
    column_searchable_list = [
        ContractorService.description,
        ContractorService.price
    ]
    column_sortable_list = [
        ContractorService.id,
        ContractorService.service_id,
        ContractorService.contractor_id
    ]
    form_columns = [
        ContractorService.service_id,
        ContractorService.contractor_id,
        ContractorService.description,
        ContractorService.price,
    ]
    column_details_list = [
        ContractorService.contractor,
        ContractorService.service,
    ]


class PortfolioItemAdmin(ModelView, model=PortfolioItem):
    column_list = [
        PortfolioItem.id,
        PortfolioItem.contractor_id,
        PortfolioItem.type,
        PortfolioItem.url,
        PortfolioItem.description,
        PortfolioItem.created_at,
        PortfolioItem.updated_at,
    ]
    column_searchable_list = [
        PortfolioItem.type,
        PortfolioItem.description
    ]
    column_sortable_list = [
        PortfolioItem.id,
        PortfolioItem.contractor_id,
        PortfolioItem.created_at
    ]
    form_columns = [
        PortfolioItem.contractor_id,
        PortfolioItem.type,
        PortfolioItem.url,
        PortfolioItem.description,
    ]
    column_details_list = [
        PortfolioItem.contractor,
    ]


class ReviewAdmin(ModelView, model=Review):
    column_list = [
        Review.id,
        Review.contractor_id,
        Review.user_id,
        Review.rating,
        Review.comment,
        Review.created_at,
    ]
    column_searchable_list = [
        Review.comment,
        Review.user_id,
        Review.contractor_id,
    ]
    column_sortable_list = [
        Review.id,
        Review.contractor_id,
        Review.created_at
    ]
    form_columns = [
        Review.contractor_id,
        Review.user_id,
        Review.rating,
        Review.comment,
    ]
    column_details_list = [
        Review.contractor,
        Review.owner,
    ]


class CategoryAdmin(ModelView, model=Category):
    name_plural = "Categories"
    column_list = [
        Category.id,
        Category.name,
        Category.description,
    ]
    column_searchable_list = [Category.name]
    column_sortable_list = [Category.id, Category.name]
    form_columns = [
        Category.name,
        Category.description,
        "services"
    ]
    column_details_list = [Category.services]

    async def create_model(self, request, data):
        services = data.pop("services", [])

        async with AsyncSessionLocal() as db:
            try:
                category = Category(**data)
                db.add(category)
                await db.commit()

                for service_data in services:
                    service = Service(category_id=category.id,
                                      **service_data)
                    db.add(service)

                await db.commit()
                return category
            except Exception as e:
                await db.rollback()
                raise e


class ServiceAdmin(ModelView, model=Service):
    column_list = [
        Service.id,
        Service.name,
        Service.category_id,
    ]
    column_searchable_list = [Service.name]
    column_sortable_list = [Service.id, Service.category_id, Service.name]
    form_columns = [
        Service.name,
        Service.category_id,
    ]
    column_details_list = [
        Service.category,
        Service.contractors_services,
    ]
