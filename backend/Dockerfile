FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências primeiro (cache de layer). Inclui dev-deps p/ rodar testes no container.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install ".[dev]"

COPY src ./src
COPY tests ./tests

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
