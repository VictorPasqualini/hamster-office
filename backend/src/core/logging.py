import logging

from .config import settings


def setup_logging() -> None:
    from .observability import RequestIdFilter

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s [rid=%(request_id)s] :: %(message)s")
    )
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level)
