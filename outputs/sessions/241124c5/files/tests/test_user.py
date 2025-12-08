import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    user_data = {"email": "newuser@test.com", "password": "securepassword"}
    response = await client.post("/users/", json=user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert "id" in data
    assert "hashed_password" not in data # Ensure password hash is not returned

@pytest.mark.asyncio
async def test_register_duplicate_user(client: AsyncClient):
    user_data = {"email": "duplicate@test.com", "password": "securepassword"}
    
    # First registration
    await client.post("/users/", json=user_data)
    
    # Second registration attempt
    response = await client.post("/users/", json=user_data)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    user_data = {"email": "login@test.com", "password": "loginpassword"}
    await client.post("/users/", json=user_data)
    
    login_data = {"username": user_data["email"], "password": user_data["password"]}
    response = await client.post("/users/token", data=login_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_failure(client: AsyncClient):
    user_data = {"email": "fail@test.com", "password": "correct"}
    await client.post("/users/", json=user_data)
    
    # Wrong password
    login_data = {"username": user_data["email"], "password": "wrong"}
    response = await client.post("/users/token", data=login_data)
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

@pytest.mark.asyncio
async def test_read_users_me(authenticated_client: tuple[AsyncClient, dict]):
    client, user_data = authenticated_client
    
    response = await client.get("/users/me")
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert "id" in data
    assert data["is_active"] is True
```