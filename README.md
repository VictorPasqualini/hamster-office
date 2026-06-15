# 🐹 Hamster Office — MVP (Full-Stack)

Escritório virtual colaborativo onde humanos e **agentes de IA (hamsters)** trabalham juntos.
Este repositório contém a **arquitetura completa** (em [`specs/`](./specs/arquitetura/README.md)), o
**backend** (FastAPI modular monolith) e o **frontend** (Next.js + TypeScript), executáveis via Docker.

## O que o MVP entrega (os 8 itens)

| # | Feature | Onde |
|---|---------|------|
| 1 | **Login** (registro, JWT access+refresh, Argon2) | `POST /api/v1/auth/*` |
| 2 | **Workspace** (multi-tenant, membros, RBAC) | `/api/v1/workspaces/*` |
| 3 | **Projetos** | `/api/v1/projects/*` |
| 4 | **Chats** (salas + WebSocket realtime + menção a agente) | `/api/v1/rooms/*`, `WS /ws` |
| 5 | **Upload de documentos** (MinIO + indexação + RAG) | `/api/v1/documents/*`, `/api/v1/knowledge/search` |
| 6 | **Agentes especializados** (Ollama/Qwen3, custos/tokens) | `/api/v1/agents/*`, `/api/v1/runs/*` |
| 7 | **Tarefas** (board, status, atribuição a humano/agente) | `/api/v1/.../tasks`, `/api/v1/tasks/*` |
| 8 | **Dashboard administrativo** (visão geral, uso/custo, auditoria) | `/api/v1/admin/*` |

## Stack

FastAPI · PostgreSQL 16 + **pgvector** · Redis · MinIO · **Ollama (Qwen3 8B)** · arq (workers) · Docker.

Decisões transversais implementadas: **multi-tenant shared-schema + Row-Level Security**,
WebSocket multiplexado com fan-out via Redis pub/sub, workers assíncronos para embeddings e
execução de agentes, billing por tokens/custo. Detalhes em [`specs/arquitetura/`](./specs/arquitetura/README.md).

## Como rodar

```bash
cp .env.example .env             # (o repo já inclui um .env de dev pronto)
docker compose up --build        # sobe db, redis, minio, migrate, api, worker, web
```

Ou use os atalhos (criam o `.env` e mostram as URLs):

```powershell
./scripts/dev.ps1 up     # Windows/PowerShell   (Linux/macOS: ./scripts/dev.sh up)
./scripts/dev.ps1 obs    # inclui Prometheus + Grafana
./scripts/dev.ps1 ai     # inclui Ollama (IA real)
./scripts/dev.ps1 test   # roda os testes dentro do container
```

| Serviço | URL | Observação |
|---------|-----|------------|
| **Web (UI)** | http://localhost:3000 | comece por aqui (login demo abaixo) |
| API / Swagger | http://localhost:8000/docs | `GET /healthz`, `/readyz`, `/metrics` |
| MinIO console | http://localhost:9001 | minioadmin / minioadmin |
| Grafana | http://localhost:3001 | profile `obs` (dashboard provisionado) |
| Prometheus | http://localhost:9090 | profile `obs` |

> IA real: `docker compose --profile ai up --build` e, no container ollama, `ollama pull qwen3:8b`.
> Sem isso, os agentes usam fallback mock (o app sobe normalmente).

> **IA com fallback**: sem o Ollama rodando (`OLLAMA_REQUIRED=false`), os agentes respondem com
> texto simulado e embeddings determinísticos — o app sobe e funciona sem GPU/modelo. Para respostas
> reais, suba com `--profile ai` e faça `ollama pull qwen3:8b`.

### Credenciais demo (seed automático)

```
email:     ana@acme.com
senha:     hamster123
workspace: acme   (use o id retornado no login no header X-Workspace-Id)
```
Já vem com 1 projeto, 1 canal `#geral` e 4 agentes especializados (Vendinha, Centavo, Bitzão, Fofuxo).

## Passo a passo rápido (curl)

```bash
# 1) Login → guarde access_token e o id do workspace
curl -s localhost:8000/api/v1/auth/login -H 'content-type: application/json' \
  -d '{"email":"ana@acme.com","password":"hamster123"}'

TOKEN=...      # access_token
WS=...         # workspaces[0].id

# 2) Listar projetos
curl -s localhost:8000/api/v1/projects -H "authorization: Bearer $TOKEN" -H "x-workspace-id: $WS"

# 3) Listar salas e mandar mensagem mencionando um agente
ROOM=$(curl -s localhost:8000/api/v1/rooms -H "authorization: Bearer $TOKEN" -H "x-workspace-id: $WS" \
  | python -c "import sys,json;print(json.load(sys.stdin)[0]['id'])")
curl -s localhost:8000/api/v1/rooms/$ROOM/messages -X POST \
  -H "authorization: Bearer $TOKEN" -H "x-workspace-id: $WS" -H 'content-type: application/json' \
  -d '{"content":"@Vendinha pode resumir o projeto?"}'
# → o worker executa o agente e posta a resposta na sala (veja em GET .../messages)

# 4) Dashboard de custos/tokens
curl -s localhost:8000/api/v1/admin/usage -H "authorization: Bearer $TOKEN" -H "x-workspace-id: $WS"
```

WebSocket (realtime): conecte em `ws://localhost:8000/ws?token=<TOKEN>&workspace_id=<WS>`,
envie `{"op":"subscribe","channel":"room:<ROOM>"}` e depois
`{"op":"message.send","channel":"room:<ROOM>","data":{"content":"@Bitzão olá"}}`.

## Estrutura

```
backend/src/
  core/         config, database (RLS), security, deps (tenant/RBAC), realtime (WS), queue, events
  db/           models SQLAlchemy (todos os schemas)
  integrations/ ollama (mock fallback), storage (MinIO)
  modules/      auth, workspace, projects, tasks, chat, knowledge, agents, office, admin
  workers/      arq: process_document, run_agent
  bootstrap.py  cria extensões, roles, schemas, tabelas, RLS e seed
  main.py       monta a API (REST /api/v1 + WS /ws)
  ../tests/     unit (sem DB) + integration (fluxo + isolamento multi-tenant)

frontend/
  app/          App Router: login, dashboard, office, projects, projects/[id], agents, admin
  components/   Sidebar, TaskBoard, ChatPanel, DocsPanel, OfficeCanvas, design system (ui.tsx)
  lib/          api (cliente), auth (contexto), ws (hooks WebSocket), iso (isométrico + A*), types
```

## Frontend (Next.js)

A UI cobre os 8 itens do MVP:

| Tela | O que faz |
|------|-----------|
| **Login** | Login/registro, seleção e troca de workspace |
| **Dashboard** | Cartões de visão geral (projetos, tarefas, agentes, tokens/custo) |
| **Escritório** | Cena isométrica (PixiJS): hamsters/colegas andam em tempo real (A* + presença via WebSocket); móveis vêm do catálogo |
| **Projetos** | Lista + criação; detalhe com abas |
| → aba **Tarefas** | Board kanban (criar, mover entre colunas, prioridade) |
| → aba **Chat** | Conversa realtime (WebSocket); menção `@Agente` aciona a IA e a resposta chega em tempo real |
| → aba **Documentos** | Upload (presigned MinIO) + indexação + teste de busca RAG |
| **Agentes** | Lista e criação de agentes especializados (persona, prompt, tools) |
| **Administração** | Consumo/custos por agente, membros e auditoria |

Rodar isolado (sem Docker):

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                        # http://localhost:3000
```

## Desenvolvimento local (sem Docker)

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate     # Windows
pip install -e .
# suba postgres(pgvector)/redis/minio localmente e ajuste .env (host=localhost)
python -m src.bootstrap
uvicorn src.main:app --reload
arq src.workers.worker.WorkerSettings               # em outro terminal
```

## Testes

```bash
cd backend
pip install -e ".[dev]"
pytest tests/unit          # rápido, sem dependências externas
pytest tests               # inclui integração: requer Postgres (senão, pulado)
```

- **Unit** (sem DB): hashing/JWT, embeddings mock (dimensão/determinismo), chunking, RBAC, menções.
- **Integração** (requer `docker compose up`): fluxo de auth + CRUD de projetos/tarefas e, principalmente,
  **isolamento multi-tenant** — um tenant não enxerga (nem acessa) dados de outro (REST + RLS).

## Observabilidade

- **Métricas Prometheus**: a API expõe `/metrics` (latência e contagem HTTP por rota/status) e o
  worker expõe métricas de negócio em `worker:9100` (execuções de agentes, tokens, custo, documentos
  indexados). Instrumentação em [observability.py](backend/src/core/observability.py).
- **Trace-id por requisição**: cada resposta tem `X-Request-Id` (gerado ou propagado), presente em
  todos os logs estruturados (`[rid=...]`).
- **Stack pronta** (`--profile obs`): **Prometheus** (scrape de api + worker) e **Grafana** com
  datasource e um **dashboard provisionado** (req/s, p95 de latência, runs/tokens/custo de IA).
  Config em [infra/observability/](infra/observability/).

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda em cada push/PR:

- **Backend**: `ruff` (lint) → sobe um Postgres (pgvector) de serviço → `python -m src.bootstrap`
  (cria schemas + RLS) → `pytest tests` (unit **e** integração, incluindo o teste de isolamento multi-tenant).
- **Frontend**: `npm ci` → `tsc --noEmit` → `next build`.

## Notas de segurança / multi-tenant

- A aplicação conecta como `app_rw` (NOSUPERUSER) e seta `app.workspace_id` por transação;
  as políticas **RLS** garantem isolamento entre workspaces nas tabelas de negócio.
- No MVP, RLS está ativa nas tabelas de alto volume (projects, tasks, chat, knowledge, agents).
  Identidade/membership usam checagem em camada de aplicação. Ver
  [`specs/arquitetura/06-multi-tenant.md`](./specs/arquitetura/06-multi-tenant.md).
- Troque `JWT_SECRET` e as credenciais padrão antes de qualquer uso real.

## Próximos passos (pós-MVP)

Sprites/assets do escritório (hoje renderizado com primitivas), edição de móveis pela UI,
aprovações human-in-the-loop completas, streaming token-a-token no chat e observabilidade.
Roadmap em [`specs/arquitetura/09-roadmap.md`](./specs/arquitetura/09-roadmap.md).
