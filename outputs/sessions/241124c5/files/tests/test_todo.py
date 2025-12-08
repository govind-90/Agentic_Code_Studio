import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_todo(authenticated_client: tuple[AsyncClient, dict]):
    client, _ = authenticated_client
    
    todo_data = {
        "title": "Buy groceries",
        "description": "Milk, eggs, bread"
    }
    
    response = await client.post("/todos/", json=todo_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy groceries"
    assert data["description"] == "Milk, eggs, bread"
    assert data["completed"] is False
    assert "id" in data

@pytest.mark.asyncio
async def test_read_todos(authenticated_client: tuple[AsyncClient, dict]):
    client, _ = authenticated_client
    
    # Create two todos
    await client.post("/todos/", json={"title": "Task 1", "description": "Desc 1"})
    await client.post("/todos/", json={"title": "Task 2", "description": "Desc 2"})
    
    response = await client.get("/todos/")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Task 1"

@pytest.mark.asyncio
async def test_read_single_todo(authenticated_client: tuple[AsyncClient, dict]):
    client, _ = authenticated_client
    
    # Create a todo
    create_response = await client.post("/todos/", json={"title": "Specific Task", "description": "Check"})
    todo_id = create_response.json()["id"]
    
    # Read the todo
    response = await client.get(f"/todos/{todo_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Specific Task"
    assert data["id"] == todo_id

@pytest.mark.asyncio
async def test_update_todo(authenticated_client: tuple[AsyncClient, dict]):
    client, _ = authenticated_client
    
    # Create a todo
    create_response = await client.post("/todos/", json={"title": "Old Title", "description": "Old Desc"})
    todo_id = create_response.json()["id"]
    
    update_data = {
        "title": "New Title",
        "description": "New Desc",
        "completed": True
    }
    
    response = await client.put(f"/todos/{todo_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["completed"] is True

@pytest.mark.asyncio
async def test_delete_todo(authenticated_client: tuple[AsyncClient, dict]):
    client, _ = authenticated_client
    
    # Create a todo
    create_response = await client.post("/todos/", json={"title": "To Delete", "description": "Gone"})
    todo_id = create_response.json()["id"]
    
    # Delete the todo
    response = await client.delete(f"/todos/{todo_id}")
    assert response.status_code == 204
    
    # Verify deletion
    verify_response = await client.get(f"/todos/{todo_id}")
    assert verify_response.status_code == 404

@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    # Attempt to access protected route without token
    response = await client.get("/todos/")
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_todo_not_found(authenticated_client: tuple[AsyncClient, dict]):
    client, _ = authenticated_client
    
    # Try to access a non-existent ID (assuming 9999 doesn't exist)
    response = await client.get("/todos/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo not found or unauthorized"