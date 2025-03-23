import os
import pytest
import pytest_asyncio
import asyncio

from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, \
    async_sessionmaker

from db.db import Base, get_db
from main import app

from test.factories import (UserFactory, ContractorFactory,
                            ContractorServiceFactory,
                            PortfolioItemFactory, ReviewFactory,
                            CategoryFactory, EventInvitationFactory,
                            EventFactory, ServiceFactory, )


load_dotenv()

TEST_DATABASE_URL = "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
    os.environ["TEST_DB_USER"],
    os.environ["TEST_DB_PASSWORD"],
    os.environ["TEST_DB_HOST"],
    os.environ["TEST_DB_PORT"],
    os.environ["TEST_DB_NAME"]
)

engine = create_async_engine(TEST_DATABASE_URL, echo=True)

TestAsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def get_test_db():
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(get_test_db):
    app.dependency_overrides[get_db] = lambda: get_test_db
    async with AsyncClient(base_url="http://testserver",
                           transport=ASGITransport(app)) as async_client:
        yield async_client


@pytest_asyncio.fixture
async def user(get_test_db: AsyncSession):
    user = await UserFactory.create(session=get_test_db, is_active=True)
    yield user


@pytest_asyncio.fixture
async def inactive_user(get_test_db):
    async with get_test_db as session:
        return await UserFactory.create(session=session, is_active=False)
