"""Fixtures de teste.

Os testes de integração só rodam se houver um PostgreSQL acessível e já inicializado
(via `docker compose up` ou `python -m src.bootstrap`). Caso contrário, são pulados.
"""

import socket

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from src.core.config import settings


def _tcp_open(url: str) -> bool:
    try:
        netloc = url.split("@", 1)[1].split("/", 1)[0]
        host, _, port = netloc.partition(":")
        with socket.create_connection((host, int(port or 5432)), timeout=1):
            return True
    except Exception:
        return False


DB_UP = _tcp_open(settings.database_url)


@pytest_asyncio.fixture
async def client():
    if not DB_UP:
        pytest.skip("PostgreSQL indisponível — suba `docker compose up` para os testes de integração")
    from src.core.database import engine
    from src.main import app

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Banco não pronto ({e})")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
