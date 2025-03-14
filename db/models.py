from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import DECIMAL
from sqlalchemy.types import Enum as SQLAEnum

from db.db import Base


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_token"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class UserRole(Enum):
    ADMIN = "admin"
    CONTRACTOR = "contractor"
    USER = "user"

    def __str__(self):
        return self.value


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    contact_data = Column(String)
    role = Column(SQLAEnum(UserRole), default=UserRole.USER.value)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=False)

    contractor = relationship("Contractor",
                              back_populates="user",
                              cascade="all, delete-orphan",
                              uselist=False)
    reviews = relationship("Review",
                           back_populates="owner",
                           cascade="all, delete-orphan")


class Contractor(Base):
    __tablename__ = "contractor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    photo = Column(String, nullable=False)
    description = Column(String, nullable=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    average_rating = Column(DECIMAL(3, 2), default=None)

    user = relationship("User",
                        back_populates="contractor",
                        single_parent=True)
    services = relationship("ContractorService",
                            back_populates="contractor",
                            cascade="all, delete-orphan")
    portfolio_items = relationship("PortfolioItem",
                                   back_populates="contractor",
                                   cascade="all, delete-orphan")
    reviews = relationship("Review",
                           back_populates="contractor",
                           cascade="all, delete-orphan")


class ContractorService(Base):
    __tablename__ = "contractor_service"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("service.id"))
    contractor_id = Column(Integer, ForeignKey("contractor.id"))
    description = Column(Text, nullable=False)
    # значение цены может быть указано "по запросу"
    price = Column(String, nullable=False)

    service = relationship("Service",
                           back_populates="contractors_services")
    contractor = relationship("Contractor",
                              back_populates="services")


class PortfolioItem(Base):
    __tablename__ = "portfolio_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contractor_id = Column(Integer, ForeignKey("contractor.id"))
    type = Column(String)
    url = Column(String)
    description = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    contractor = relationship("Contractor",
                              back_populates="portfolio_items")


class Review(Base):
    __tablename__ = "review"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contractor_id = Column(Integer, ForeignKey("contractor.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(DECIMAL(3, 2))
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))

    contractor = relationship("Contractor", back_populates="reviews")
    owner = relationship("User", back_populates="reviews")


class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)

    services = relationship("Service",
                            back_populates="category",
                            cascade="all, delete-orphan")


class Service(Base):
    __tablename__ = "service"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    category_id = Column(Integer, ForeignKey("category.id"))

    category = relationship("Category", back_populates="services")
    contractors_services = relationship("ContractorService",
                                        back_populates="service",
                                        cascade="all, delete-orphan")
