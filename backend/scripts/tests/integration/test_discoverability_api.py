import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_candidates_empty(client: AsyncClient):
    response = await client.get("/api/candidates")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_get_candidate_not_found(client: AsyncClient):
    response = await client.get("/api/candidates/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found."


@pytest.mark.anyio
async def test_list_projects_empty(client: AsyncClient):
    response = await client.get("/api/projects")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_get_project_not_found(client: AsyncClient):
    response = await client.get("/api/projects/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found."
