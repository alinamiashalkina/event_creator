from typing import Optional
from pydantic import BaseModel, Field, PositiveInt


class CategoryCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class CategorySchema(BaseModel):
    id: int
    name: str = Field(..., min_length=3)
    description: Optional[str] = None

    class Config:
        from_attributes = True


class CategoryUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ServiceCreateSchema(BaseModel):
    name: str = Field(..., min_length=3)
    category_id: Optional[PositiveInt] = None

    class Config:
        from_attributes = True


class ServiceUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=3)
    category_id: Optional[PositiveInt] = None

    class Config:
        from_attributes = True


class ServiceSchema(BaseModel):
    id: int
    name: str = Field(..., min_length=3)
    category_id: PositiveInt

    class Config:
        from_attributes = True
