import factory
import factory.fuzzy

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, Contractor, ContractorService, PortfolioItem, \
    Review, Category, Service, Event, EventInvitation, EventInvitationStatus

from auth.auth import hash_password
from db.models import UserRole

fake = Faker()


class AsyncFactory(factory.Factory):

    class Meta:
        abstract = True

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs):
        obj = cls.build(**kwargs)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


class UserFactory(AsyncFactory):
    class Meta:
        model = User

    username = factory.Faker('user_name')
    email = factory.Faker('email')
    password_hash = factory.LazyFunction(lambda: hash_password("testpassword"))
    name = factory.Faker('name')
    contact_data = factory.Faker('phone_number')
    role = factory.fuzzy.FuzzyChoice(list(UserRole))
    is_active = factory.Faker('boolean', chance_of_getting_true=70)


class ContractorFactory(AsyncFactory):
    class Meta:
        model = Contractor

    photo = factory.Faker('image_url')
    description = factory.Faker('text', max_nb_chars=200)
    is_approved = factory.Faker('boolean', chance_of_getting_true=50)
    user = factory.SubFactory(UserFactory)


class ContractorServiceFactory(AsyncFactory):
    class Meta:
        model = ContractorService

    service_id = factory.Faker('random_int', min=1, max=100)
    contractor = factory.SubFactory(ContractorFactory)
    description = factory.Faker('text', max_nb_chars=200)
    price = factory.Faker('random_number', digits=5)


class PortfolioItemFactory(AsyncFactory):
    class Meta:
        model = PortfolioItem

    contractor = factory.SubFactory(ContractorFactory)
    type = factory.Faker('word')
    url = factory.Faker('url')
    description = factory.Faker('text', max_nb_chars=200)


class ReviewFactory(AsyncFactory):
    class Meta:
        model = Review

    contractor = factory.SubFactory(ContractorFactory)
    user = factory.SubFactory(UserFactory)
    rating = factory.Faker('random_number', digits=1)
    comment = factory.Faker('text', nullable=True)


class CategoryFactory(AsyncFactory):
    class Meta:
        model = Category

    name = factory.Faker('word')
    description = factory.Faker('text', max_nb_chars=200)


class ServiceFactory(AsyncFactory):
    class Meta:
        model = Service

    name = factory.Faker('word')
    category = factory.SubFactory(CategoryFactory)


class EventFactory(AsyncFactory):
    class Meta:
        model = Event

    user_id = factory.SubFactory(UserFactory)
    name = factory.Faker('sentence', nb_words=4)
    date_time = factory.Faker('future_datetime', end_date="+30d")


class EventInvitationFactory(AsyncFactory):
    class Meta:
        model = EventInvitation

    event = factory.SubFactory(EventFactory)
    recipient = factory.SubFactory(ContractorFactory)
    sender = factory.SubFactory(UserFactory)
    status = factory.fuzzy.FuzzyChoice(list(EventInvitationStatus))
