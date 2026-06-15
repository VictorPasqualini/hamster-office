"""Entrypoint do worker arq.  Rode com:  arq src.workers.worker.WorkerSettings"""

import logging

from ..core.logging import setup_logging
from ..core.queue import redis_settings
from ..integrations import storage
from .jobs import process_document, run_agent


async def on_startup(ctx) -> None:
    setup_logging()
    # Expõe métricas Prometheus do worker (scrape em worker:9100/metrics)
    try:
        from prometheus_client import start_http_server

        start_http_server(9100)
    except Exception as e:  # noqa: BLE001
        logging.getLogger("worker").warning("Métricas do worker não iniciadas: %s", e)
    try:
        storage.ensure_bucket()
    except Exception as e:  # noqa: BLE001
        logging.getLogger("worker").warning("Bucket MinIO não verificado: %s", e)


class WorkerSettings:
    functions = [process_document, run_agent]
    redis_settings = redis_settings()
    on_startup = on_startup
    max_jobs = 10
    job_timeout = 180
