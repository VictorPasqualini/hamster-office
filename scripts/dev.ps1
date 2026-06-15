<#
.SYNOPSIS
  Atalhos para rodar o Hamster Office localmente (Windows / PowerShell).

.EXAMPLE
  ./scripts/dev.ps1 up        # sobe a stack (db, redis, minio, api, worker, web)
  ./scripts/dev.ps1 obs       # sobe também Prometheus + Grafana
  ./scripts/dev.ps1 ai        # sobe também o Ollama (IA real)
  ./scripts/dev.ps1 logs      # acompanha os logs
  ./scripts/dev.ps1 down      # derruba tudo
  ./scripts/dev.ps1 test      # roda os testes do backend
  ./scripts/dev.ps1 urls      # mostra os endereços
#>
param([Parameter(Position = 0)][string]$cmd = "up")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "$root/.env")) {
  Copy-Item "$root/.env.example" "$root/.env"
  Write-Host "Criado .env a partir de .env.example" -ForegroundColor Yellow
}

function Show-Urls {
  Write-Host ""
  Write-Host "  Web (UI):     http://localhost:3000   (login: ana@acme.com / hamster123)" -ForegroundColor Green
  Write-Host "  API (Swagger):http://localhost:8000/docs"
  Write-Host "  MinIO:        http://localhost:9001   (minioadmin / minioadmin)"
  Write-Host "  Grafana:      http://localhost:3001   (anônimo/admin)  [profile obs]"
  Write-Host "  Prometheus:   http://localhost:9090                    [profile obs]"
  Write-Host ""
}

switch ($cmd) {
  "up"   { docker compose up --build -d; Show-Urls }
  "obs"  { docker compose --profile obs up --build -d; Show-Urls }
  "ai"   { docker compose --profile ai up --build -d; Show-Urls }
  "all"  { docker compose --profile obs --profile ai up --build -d; Show-Urls }
  "down" { docker compose --profile obs --profile ai down }
  "logs" { docker compose logs -f --tail=100 }
  "ps"   { docker compose ps }
  "seed" { docker compose run --rm migrate python -m src.bootstrap }
  "test" { docker compose exec api pytest tests -q }
  "urls" { Show-Urls }
  default { Write-Host "Comando desconhecido: $cmd"; Write-Host "Use: up | obs | ai | all | down | logs | ps | seed | test | urls" }
}
