"""Observabilidade: métricas Prometheus, trace-id por requisição e log estruturado.

- `/metrics` (no app) expõe métricas HTTP da API.
- O worker expõe métricas próprias (ver workers/worker.py) na porta 9100.
- Cada requisição recebe um `X-Request-Id` (gerado ou propagado) presente nos logs.
"""

import logging
import time
import uuid
from contextvars import ContextVar

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

# ---- métricas HTTP (processo da API) ----
HTTP_REQUESTS = Counter(
    "http_requests_total", "Total de requisições HTTP", ["method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds", "Latência das requisições HTTP", ["method", "path"]
)

# ---- métricas de negócio (incrementadas no worker) ----
AGENT_RUNS = Counter("agent_runs_total", "Execuções de agentes", ["status"])
AGENT_TOKENS = Counter("agent_tokens_total", "Tokens consumidos pelos agentes")
AGENT_COST = Counter("agent_cost_usd_total", "Custo acumulado (USD) dos agentes")
DOCS_INDEXED = Counter("documents_indexed_total", "Documentos indexados")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request_id_ctx.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            duration = time.perf_counter() - start
            route = request.scope.get("route")
            path = getattr(route, "path", None) or "unmatched"
            HTTP_REQUESTS.labels(request.method, path, str(status)).inc()
            HTTP_LATENCY.labels(request.method, path).observe(duration)
            logging.getLogger("http").info(
                "%s %s -> %s (%.1fms) rid=%s",
                request.method,
                path,
                status,
                duration * 1000,
                rid,
            )
        response.headers["X-Request-Id"] = rid
        return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
