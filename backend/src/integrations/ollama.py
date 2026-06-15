"""Cliente Ollama com fallback mock.

Se o Ollama não estiver acessível e OLLAMA_REQUIRED=false, cai para respostas e embeddings
determinísticos simulados — o app sobe e funciona sem GPU/modelo baixado. Em produção,
defina OLLAMA_REQUIRED=true.
"""

import hashlib
import logging
import math

import httpx

from ..core.config import settings

log = logging.getLogger("ollama")

# Preço fictício por 1k tokens (apenas para ilustrar billing local).
PRICE_PER_1K_TOKENS = 0.0002


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round((prompt_tokens + completion_tokens) / 1000 * PRICE_PER_1K_TOKENS, 6)


class OllamaClient:
    def __init__(self) -> None:
        self.base = settings.ollama_url.rstrip("/")
        self.chat_model = settings.ollama_chat_model
        self.embed_model = settings.ollama_embed_model
        self.dim = settings.embed_dim
        self.required = settings.ollama_required

    async def _available(self, client: httpx.AsyncClient) -> bool:
        try:
            r = await client.get(f"{self.base}/api/tags", timeout=2.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def chat(self, system: str, prompt: str) -> dict:
        """Retorna {content, prompt_tokens, completion_tokens, cost_usd, mocked}."""
        async with httpx.AsyncClient() as client:
            if await self._available(client):
                try:
                    r = await client.post(
                        f"{self.base}/api/chat",
                        json={
                            "model": self.chat_model,
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": prompt},
                            ],
                            "stream": False,
                        },
                        timeout=120.0,
                    )
                    r.raise_for_status()
                    data = r.json()
                    content = data.get("message", {}).get("content", "")
                    pt = data.get("prompt_eval_count") or _approx_tokens(system + prompt)
                    ct = data.get("eval_count") or _approx_tokens(content)
                    return {
                        "content": content,
                        "prompt_tokens": pt,
                        "completion_tokens": ct,
                        "cost_usd": estimate_cost(pt, ct),
                        "mocked": False,
                    }
                except httpx.HTTPError as e:
                    log.warning("Falha no Ollama chat: %s", e)
                    if self.required:
                        raise
            elif self.required:
                raise RuntimeError("Ollama indisponível e OLLAMA_REQUIRED=true")

        return self._mock_chat(system, prompt)

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            if await self._available(client):
                try:
                    r = await client.post(
                        f"{self.base}/api/embeddings",
                        json={"model": self.embed_model, "prompt": text},
                        timeout=60.0,
                    )
                    r.raise_for_status()
                    emb = r.json().get("embedding")
                    if emb:
                        return self._fit_dim(emb)
                except httpx.HTTPError as e:
                    log.warning("Falha no Ollama embed: %s", e)
                    if self.required:
                        raise
            elif self.required:
                raise RuntimeError("Ollama indisponível e OLLAMA_REQUIRED=true")
        return self._mock_embed(text)

    # ---- mocks determinísticos ----
    def _mock_chat(self, system: str, prompt: str) -> dict:
        snippet = prompt.strip().splitlines()[0][:160] if prompt.strip() else ""
        content = (
            "[resposta simulada — Ollama indisponível] "
            f"Recebi sua mensagem e, com base no meu papel, eis um encaminhamento: '{snippet}'. "
            "Configure o Ollama (perfil 'ai') para respostas reais."
        )
        pt, ct = _approx_tokens(system + prompt), _approx_tokens(content)
        return {
            "content": content,
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "cost_usd": estimate_cost(pt, ct),
            "mocked": True,
        }

    def _mock_embed(self, text: str) -> list[float]:
        # Vetor determinístico a partir do hash do texto, normalizado.
        seed = hashlib.sha256(text.encode()).digest()
        vals = [((seed[i % len(seed)] / 255.0) * 2 - 1) for i in range(self.dim)]
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]

    def _fit_dim(self, emb: list[float]) -> list[float]:
        if len(emb) == self.dim:
            return emb
        if len(emb) > self.dim:
            return emb[: self.dim]
        return emb + [0.0] * (self.dim - len(emb))


ollama = OllamaClient()
