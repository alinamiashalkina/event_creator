import pytest
from sqlalchemy.future import select

from db.models import BlacklistedToken
from test.conftest import get_test_db


@pytest.mark.asyncio
async def test_login_success(client, user):
    login_data = {"username": user.username, "password": "testpassword"}

    response = await client.post("/login", data=login_data)

    assert response.status_code == 200
    assert response.json() == {"msg": "Login successful"}

    cookies = response.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies


@pytest.mark.asyncio
async def test_login_user_not_found(client):
    login_data = {"username": "nonexistent_user", "password": "testpassword"}

    response = await client.post("/login", data=login_data)

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


@pytest.mark.asyncio
async def test_login_account_inactive(client, inactive_user):

    login_data = {"username": inactive_user.username,
                  "password": "testpassword"}

    response = await client.post("/login", data=login_data)

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Account is not active. Please wait for admin approval."
    }


@pytest.mark.asyncio
async def test_logout(client, user, get_test_db):
    login_data = {"username": user.username, "password": "testpassword"}
    login_response = await client.post("/login", data=login_data)

    assert "access_token" in login_response.cookies
    assert "refresh_token" in login_response.cookies

    access_token = login_response.cookies["access_token"]

    logout_response = await client.post(
        "/logout", cookies={"access_token": access_token}
    )

    assert logout_response.status_code == 200
    assert logout_response.json() == {"message": "Logged out successfully"}

    cookies = logout_response.cookies
    assert "access_token" not in cookies or cookies["access_token"] == ""
    assert "refresh_token" not in cookies or cookies["refresh_token"] == ""

    async with get_test_db as t_db:
        access_token = login_response.cookies["access_token"]
        refresh_token = login_response.cookies["refresh_token"]

        result = await t_db.execute(
            select(BlacklistedToken)
            .where(BlacklistedToken.token == access_token)
        )

        blacklisted_access_token = result.scalars().first()
        assert blacklisted_access_token is not None

        result = await t_db.execute(
            select(BlacklistedToken)
            .where(BlacklistedToken.token == refresh_token)
        )

        blacklisted_refresh_token = result.scalars().first()
        assert blacklisted_refresh_token is not None


@pytest.mark.asyncio
async def test_auth_middleware_public_endpoint(client):
    client.cookies.clear()
    response = await client.get("/login")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_middleware_protected_endpoint_valid_token(client, user):
    client.cookies.clear()
    login_data = {"username": user.username, "password": "testpassword"}
    login_response = await client.post("/login", data=login_data)
    access_token = login_response.cookies["access_token"]

    response = await client.get("/contractors",
                                cookies={"access_token": access_token})
    assert response.status_code == 200
