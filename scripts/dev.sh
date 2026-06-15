#!/usr/bin/env bash
# Atalhos para rodar o Hamster Office localmente (Linux/macOS/WSL).
#   ./scripts/dev.sh up | obs | ai | all | down | logs | ps | seed | test | urls
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { cp .env.example .env; echo "Criado .env a partir de .env.example"; }

urls() {
  cat <<EOF

  Web (UI):      http://localhost:3000   (login: ana@acme.com / hamster123)
  API (Swagger): http://localhost:8000/docs
  MinIO:         http://localhost:9001   (minioadmin / minioadmin)
  Grafana:       http://localhost:3001   [profile obs]
  Prometheus:    http://localhost:9090   [profile obs]

EOF
}

case "${1:-up}" in
  up)   docker compose up --build -d; urls ;;
  obs)  docker compose --profile obs up --build -d; urls ;;
  ai)   docker compose --profile ai up --build -d; urls ;;
  all)  docker compose --profile obs --profile ai up --build -d; urls ;;
  down) docker compose --profile obs --profile ai down ;;
  logs) docker compose logs -f --tail=100 ;;
  ps)   docker compose ps ;;
  seed) docker compose run --rm migrate python -m src.bootstrap ;;
  test) docker compose exec api pytest tests -q ;;
  urls) urls ;;
  *)    echo "Use: up | obs | ai | all | down | logs | ps | seed | test | urls" ;;
esac
