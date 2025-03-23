from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, PositiveInt, condecimal

from db.models import UserRole
from service.schemas import ServiceSchema


class UserRegistrationSchema(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=3)
    contact_data: Optional[str] = None

    class Config:
        from_attributes = True


class UserOutSchema(BaseModel):
    id: PositiveInt
    username: str = Field(..., min_length=3)
    email: EmailStr
    name: str = Field(..., min_length=3)
    role: UserRole
    contact_data: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    contact_data: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True


class ReviewListSchema(BaseModel):
    id: PositiveInt
    user_id: PositiveInt
    rating: Decimal
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCreateSchema(BaseModel):
    rating: Decimal
    comment: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewSchema(BaseModel):
    id: PositiveInt
    contractor_id: PositiveInt
    user_id: PositiveInt
    rating: Decimal
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ContractorServiceListSchema(BaseModel):
    service: ServiceSchema
    id: PositiveInt

    class Config:
        from_attributes = True


class ContractorServiceSchema(BaseModel):
    service: ServiceSchema
    description: str = Field(..., min_length=5)
    price: str = Field(..., min_length=3)

    class Config:
        from_attributes = True


class ContractorServiceCreateSchema(BaseModel):
    service_id: Optional[PositiveInt] = None
    contractor_id: Optional[PositiveInt] = None
    description: str = Field(..., min_length=5)
    price: str = Field(..., min_length=3)

    class Config:
        from_attributes = True


class ContractorServiceUpdateSchema(BaseModel):
    description: Optional[str] = Field(None, min_length=5)
    price: Optional[str] = Field(None, min_length=3)

    class Config:
        from_attributes = True


class PortfolioItemSchema(BaseModel):
    id: PositiveInt
    type: str
    url: str
    description: str = Field(..., min_length=5)
    updated_at: datetime

    class Config:
        from_attributes = True


class PortfolioItemAddSchema(BaseModel):
    contractor_id: Optional[PositiveInt] = None
    type: str
    url: str
    description: str = Field(..., min_length=5)

    class Config:
        from_attributes = True


class PortfolioItemUpdateSchema(BaseModel):
    type: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = Field(None, min_length=5)

    class Config:
        from_attributes = True


class ContractorRegistrationSchema(BaseModel):
    user: UserRegistrationSchema
    photo: str
    description: str = Field(..., min_length=5)
    services: List[ContractorServiceCreateSchema]
    portfolio_items: Optional[List[PortfolioItemAddSchema]] = None

    class Config:
        from_attributes = True


class ContractorApplicationListSchema(BaseModel):
    id: PositiveInt
    user: UserOutSchema
    description: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContractorApplicationSchema(BaseModel):
    id: PositiveInt = Field(...)
    user: UserOutSchema
    photo: str
    description: str
    is_approved: bool
    created_at: datetime
    updated_at: datetime
    services: List[ContractorServiceSchema]
    portfolio_items: Optional[List[PortfolioItemSchema]] = []

    class Config:
        from_attributes = True


class ContractorSchema(BaseModel):
    id: PositiveInt = Field(...)
    user_id: PositiveInt
    description: str
    is_approved: bool
    created_at: datetime
    average_rating: condecimal(max_digits=3, decimal_places=2) | None

    class Config:
        from_attributes = True


class ContractorOutSchema(BaseModel):
    id: PositiveInt = Field(...)
    user: UserOutSchema
    photo: str
    description: str
    is_approved: bool
    created_at: datetime
    updated_at: datetime
    average_rating: condecimal(max_digits=3, decimal_places=2) | None
    services: List[ContractorServiceSchema]
    portfolio_items: Optional[List[PortfolioItemSchema]] = []

    class Config:
        from_attributes = True


class ContractorUpdateSchema(BaseModel):
    user: UserUpdateSchema
    photo: Optional[str] = None
    description: Optional[str] = None
    is_approved: Optional[bool] = None

    class Config:
        from_attributes = True
