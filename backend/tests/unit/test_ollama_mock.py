import math

from src.core.config import settings
from src.integrations.ollama import estimate_cost, ollama


def test_mock_embed_dimension_and_determinism():
    a = ollama._mock_embed("contrato de prestação de serviços")
    b = ollama._mock_embed("contrato de prestação de serviços")
    assert len(a) == settings.embed_dim
    assert a == b  # determinístico
    norm = math.sqrt(sum(v * v for v in a))
    assert abs(norm - 1.0) < 1e-6  # normalizado


def test_mock_embed_differs_for_different_text():
    assert ollama._mock_embed("a") != ollama._mock_embed("b")


def test_fit_dim_pads_and_truncates():
    assert len(ollama._fit_dim([0.1, 0.2])) == settings.embed_dim
    assert len(ollama._fit_dim([0.0] * (settings.embed_dim + 50))) == settings.embed_dim


def test_estimate_cost_monotonic():
    assert estimate_cost(0, 0) == 0
    assert estimate_cost(1000, 1000) > estimate_cost(500, 500)


def test_mock_chat_shape():
    r = ollama._mock_chat("system", "olá")
    assert r["mocked"] is True
    assert {"content", "prompt_tokens", "completion_tokens", "cost_usd"} <= r.keys()
