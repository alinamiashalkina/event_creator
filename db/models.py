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
    expires_at = Column(DateTime(timezone=True), nullable=False)


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
    role = Column(SQLAEnum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=False)

    contractor = relationship("Contractor",
                              back_populates="user",
                              foreign_keys="[Contractor.user_id]",
                              cascade="all, delete-orphan",
                              uselist=False)
    reviews = relationship("Review",
                           back_populates="owner",
                           foreign_keys="[Review.user_id]",
                           cascade="all, delete-orphan")
    created_events = relationship("Event",
                                  back_populates="user",
                                  foreign_keys="[Event.user_id]",
                                  cascade="all, delete-orphan")
    organized_events = relationship("Event",
                                    back_populates="organizer",
                                    foreign_keys="[Event.organizer_id]",
                                    cascade="all, delete-orphan")
    sent_invitations = relationship("EventInvitation",
                                    back_populates="sender",
                                    foreign_keys="[EventInvitation.sender_id]",
                                    cascade="all, delete-orphan")

    def __repr__(self):
        return f"User(id={self.id}, username={self.username})"


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
                        foreign_keys=[user_id],
                        single_parent=True)
    services = relationship("ContractorService",
                            back_populates="contractor",
                            foreign_keys="[ContractorService.contractor_id]",
                            cascade="all, delete-orphan")
    portfolio_items = relationship(
        "PortfolioItem",
        back_populates="contractor",
        foreign_keys="[PortfolioItem.contractor_id]",
        cascade="all, delete-orphan"
    )
    reviews = relationship("Review",
                           back_populates="contractor",
                           foreign_keys="[Review.contractor_id]",
                           cascade="all, delete-orphan")
    invitations = relationship("EventInvitation",
                               back_populates="contractor",
                               foreign_keys="[EventInvitation.recipient_id]",
                               cascade="all, delete-orphan")

    def __repr__(self):
        return (f"Contractor(id={self.id}, user_id={self.user_id}, "
                f"is_approved={self.is_approved})")


class ContractorService(Base):
    __tablename__ = "contractor_service"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("service.id"))
    contractor_id = Column(Integer, ForeignKey("contractor.id"))
    description = Column(Text, nullable=False)
    # значение цены может быть указано "по запросу"
    price = Column(String, nullable=False)

    service = relationship("Service",
                           back_populates="contractors_services",
                           foreign_keys=[service_id])
    contractor = relationship("Contractor",
                              back_populates="services",
                              foreign_keys=[contractor_id])

    def __repr__(self):
        return (f"ContractorService(id={self.id}, "
                f"service_id={self.service_id}, "
                f"contractor_id={self.contractor_id})")


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
                              back_populates="portfolio_items",
                              foreign_keys=[contractor_id])

    def __repr__(self):
        return (f"PortfolioItem(id={self.id}, "
                f"contractor_id={self.contractor_id}, "
                f"type={self.type})")


class Review(Base):
    __tablename__ = "review"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contractor_id = Column(Integer, ForeignKey("contractor.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(DECIMAL(3, 2))
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))

    contractor = relationship("Contractor",
                              back_populates="reviews",
                              foreign_keys=[contractor_id])
    owner = relationship("User",
                         foreign_keys=[user_id],
                         back_populates="reviews")

    def __repr__(self):
        return (f"Review(id={self.id}, contractor_id={self.contractor_id}, "
                f"user_id={self.user_id}, comment={self.comment}, "
                f"rating={self.rating})")


class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)

    services = relationship("Service",
                            back_populates="category",
                            foreign_keys="[Service.category_id]",
                            cascade="all, delete-orphan")

    def __repr__(self):
        return f"Category(id={self.id}, name={self.name})"


class Service(Base):
    __tablename__ = "service"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    category_id = Column(Integer, ForeignKey("category.id"))

    category = relationship("Category",
                            back_populates="services",
                            foreign_keys=[category_id])
    contractors_services = relationship(
        "ContractorService",
        back_populates="service",
        foreign_keys="[ContractorService.service_id]",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (f"Service(id={self.id}, name={self.name}, "
                f"category_id={self.category_id})")


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User",
                        back_populates="created_events",
                        foreign_keys=[user_id])
    organizer = relationship("User",
                             back_populates="organized_events",
                             foreign_keys=[organizer_id])
    invitations = relationship("EventInvitation",
                               back_populates="event",
                               foreign_keys="[EventInvitation.event_id]",
                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"Event(id={self.id}, name={self.name}, user_id={self.user_id})"


class EventInvitationStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CONFIRMED = "confirmed"
    CANCELED = "canceled"

    def __str__(self):
        return self.value


class EventInvitation(Base):
    __tablename__ = "event_invitation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("contractor.id"),
                          nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(SQLAEnum(EventInvitationStatus),
                    default=EventInvitationStatus.PENDING)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    event = relationship("Event",
                         back_populates="invitations",
                         foreign_keys=[event_id])
    contractor = relationship("Contractor",
                              foreign_keys=[recipient_id])
    sender = relationship("User",
                          foreign_keys=[sender_id])

    def __repr__(self):
        return (
            f"EventInvitation(id={self.id}, event_id={self.event_id}, "
            f"sender_id={self.sender_id}, recipient_id={self.recipient_id},"
            f"status={self.status})"
        )
