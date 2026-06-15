"""Fluxo ponta a ponta + isolamento multi-tenant (requer PostgreSQL inicializado)."""

import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def _register(client, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"name": "Tester", "email": email, "password": "pw123456"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


async def _create_workspace(client, token: str, slug: str) -> str:
    r = await client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": slug, "slug": slug},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _h(token: str, ws: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws}


async def test_auth_and_project_crud(client):
    suffix = uuid.uuid4().hex[:8]
    token = await _register(client, f"u-{suffix}@test.com")
    ws = await _create_workspace(client, token, f"ws-{suffix}")

    # cria projeto
    r = await client.post("/api/v1/projects", headers=_h(token, ws), json={"name": "Projeto X"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    # lista contém o projeto
    r = await client.get("/api/v1/projects", headers=_h(token, ws))
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())


async def test_task_status_flow(client):
    suffix = uuid.uuid4().hex[:8]
    token = await _register(client, f"u-{suffix}@test.com")
    ws = await _create_workspace(client, token, f"ws-{suffix}")
    pid = (
        await client.post("/api/v1/projects", headers=_h(token, ws), json={"name": "P"})
    ).json()["id"]

    r = await client.post(
        f"/api/v1/projects/{pid}/tasks",
        headers=_h(token, ws),
        json={"title": "Fazer algo", "priority": "high"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    assert r.json()["status"] == "todo"

    r = await client.post(
        f"/api/v1/tasks/{tid}/status", headers=_h(token, ws), json={"status": "in_progress"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"


async def test_tenant_isolation(client):
    suffix = uuid.uuid4().hex[:8]
    # Tenant A com um projeto
    token_a = await _register(client, f"a-{suffix}@test.com")
    ws_a = await _create_workspace(client, token_a, f"a-{suffix}")
    pid = (
        await client.post("/api/v1/projects", headers=_h(token_a, ws_a), json={"name": "Secreto A"})
    ).json()["id"]

    # Tenant B (outro usuário/workspace)
    token_b = await _register(client, f"b-{suffix}@test.com")
    ws_b = await _create_workspace(client, token_b, f"b-{suffix}")

    # B não pode usar o workspace de A (não é membro) → 403
    r = await client.get("/api/v1/projects", headers=_h(token_b, ws_a))
    assert r.status_code == 403

    # B no próprio workspace não enxerga o projeto de A (RLS)
    r = await client.get("/api/v1/projects", headers=_h(token_b, ws_b))
    assert r.status_code == 200
    assert all(p["id"] != pid for p in r.json())

    # A também não acessa o workspace de B
    r = await client.get("/api/v1/projects", headers=_h(token_a, ws_b))
    assert r.status_code == 403
