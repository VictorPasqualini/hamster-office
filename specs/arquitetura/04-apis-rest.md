# APIs REST

> Contrato HTTP do backend FastAPI. Base: `/api/v1`. Tempo real fica em [05-websockets.md](./05-websockets.md).

## 1. Convenções gerais

- **Base URL**: `https://{tenant-host}/api/v1` ou header `X-Workspace-Slug` / path `/w/{slug}`.
- **Auth**: `Authorization: Bearer <access_token>` (JWT, 15 min). Refresh via cookie httpOnly rotacionado.
- **Tenant**: derivado do JWT (`workspace_id` no claim) e/ou slug. Middleware seta `app.workspace_id` (RLS).
- **Formato**: JSON; `snake_case`; datas ISO-8601 UTC.
- **Paginação**: cursor — `?limit=50&cursor=<opaque>`; resposta `{ "items": [...], "next_cursor": "..." }`.
- **Idempotência**: header `Idempotency-Key` em POSTs sensíveis (uploads, aprovações).
- **Erros** (RFC 7807 / problem+json):

```json
{ "type": "https://errors.hamster.office/validation",
  "title": "Validation failed",
  "status": 422,
  "detail": "field 'email' is invalid",
  "trace_id": "..." }
```

- **Rate limit**: por tenant e por usuário (headers `X-RateLimit-*`); 429 com `Retry-After`.
- **Versionamento**: prefixo `/v1`; mudanças incompatíveis → `/v2`.

## 2. Códigos de status

`200` ok · `201` criado · `202` aceito (processamento assíncrono) · `204` sem conteúdo ·
`400` requisição inválida · `401` não autenticado · `403` sem permissão (RBAC) · `404` ·
`409` conflito · `422` validação · `429` rate limit · `500` erro interno.

## 3. Matriz de permissões (RBAC resumida)

| Recurso / ação | admin | manager | collaborator | guest |
|----------------|:-----:|:-------:|:------------:|:-----:|
| Workspace settings | ✅ | ➖ | ❌ | ❌ |
| Convidar membros | ✅ | ✅ | ❌ | ❌ |
| Criar projeto | ✅ | ✅ | ✅ | ❌ |
| Criar/editar tarefa | ✅ | ✅ | ✅ | ❌ |
| Enviar mensagem | ✅ | ✅ | ✅ | ✅¹ |
| Upload documento | ✅ | ✅ | ✅ | ❌ |
| Config. agentes | ✅ | ✅ | ❌ | ❌ |
| Aprovar ações | ✅ | ✅ | ❌ | ❌ |
| Ver auditoria/custos | ✅ | ✅² | ❌ | ❌ |
| Editar escritório | ✅ | ✅ | ➖³ | ❌ |

¹ apenas em salas do projeto a que foi convidado · ² somente leitura · ³ configurável.

---

## 4. Endpoints por módulo

### 4.1 Auth (`/auth`)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/auth/register` | Cria usuário global |
| POST | `/auth/login` | Retorna access+refresh; lista workspaces do usuário |
| POST | `/auth/refresh` | Rotaciona refresh, novo access |
| POST | `/auth/logout` | Revoga refresh atual |
| POST | `/auth/password/reset-request` | Envia email de reset |
| POST | `/auth/password/reset` | Aplica nova senha |
| GET | `/auth/me` | Perfil + memberships |

```http
POST /api/v1/auth/login
{ "email": "ana@acme.com", "password": "•••" }
→ 200 { "access_token":"…", "user":{…}, "workspaces":[{"id","slug","role"}] }
```

### 4.2 Workspaces (`/workspaces`)

| Método | Rota | Papel mín. |
|--------|------|-----------|
| POST | `/workspaces` | usuário autenticado (vira admin) |
| GET | `/workspaces` | — (os meus) |
| GET | `/workspaces/{id}` | member |
| PATCH | `/workspaces/{id}` | admin |
| GET/PATCH | `/workspaces/{id}/settings` | admin |
| POST | `/workspaces/{id}/invites` | manager+ |
| POST | `/invites/{token}/accept` | autenticado |
| GET | `/workspaces/{id}/members` | member |
| PATCH | `/workspaces/{id}/members/{mid}` | admin (role/status) |
| DELETE | `/workspaces/{id}/members/{mid}` | admin |

### 4.3 Projects (`/projects`)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/projects` | cria projeto |
| GET | `/projects` | lista (filtros: status, cliente) |
| GET | `/projects/{id}` | detalhe |
| PATCH | `/projects/{id}` | edita / arquiva |
| POST | `/projects/{id}/members` | adiciona participante |
| DELETE | `/projects/{id}/members/{mid}` | remove |
| POST | `/projects/{id}/agents` | associa agente |
| DELETE | `/projects/{id}/agents/{aid}` | desassocia |
| GET | `/projects/{id}/overview` | resumo (tarefas, salas, arquivos, agentes) |

### 4.4 Tasks (`/tasks`)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/projects/{pid}/tasks` | cria tarefa |
| GET | `/projects/{pid}/tasks` | lista/board (filtros: status, assignee, priority) |
| GET | `/tasks/{id}` | detalhe + atividade |
| PATCH | `/tasks/{id}` | edita |
| POST | `/tasks/{id}/status` | transição de status |
| POST | `/tasks/{id}/assign` | atribui a user/agente |
| POST | `/tasks/{id}/comments` | comenta |
| GET | `/tasks/{id}/activity` | histórico |

```http
POST /api/v1/tasks/{id}/assign
{ "assignee_kind": "agent", "assignee_id": "…" }   # delega a um agente
```

### 4.5 Chat (`/rooms`, `/messages`)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/rooms` | cria sala (channel/dm/human_agent) |
| GET | `/rooms` | lista salas visíveis |
| GET | `/rooms/{id}` | detalhe + participantes |
| POST | `/rooms/{id}/participants` | adiciona (humano ou agente) |
| GET | `/rooms/{id}/messages` | histórico (cursor, `before`/`after`) |
| POST | `/rooms/{id}/messages` | envia (fallback HTTP do WS) |
| PATCH | `/messages/{id}` | edita (gera versão) |
| POST | `/messages/{id}/reactions` | reage |
| POST | `/rooms/{id}/read` | marca lido (`last_read_message_id`) |

> O envio em tempo real é via WebSocket; o POST HTTP existe como fallback e para integrações.

### 4.6 Documents & Knowledge (`/documents`)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/documents/upload-url` | retorna URL pré-assinada do MinIO |
| POST | `/documents` | registra documento após upload → enfileira indexação (202) |
| GET | `/documents` | lista (filtros: project, status) |
| GET | `/documents/{id}` | metadados + status de indexação |
| GET | `/documents/{id}/download-url` | URL assinada de download |
| POST | `/documents/{id}/versions` | nova versão |
| DELETE | `/documents/{id}` | exclusão (pode exigir aprovação) |
| POST | `/knowledge/search` | busca semântica (RAG) — uso interno/agentes e debug |

```http
POST /api/v1/knowledge/search
{ "query": "cláusula de rescisão", "project_id": "…", "top_k": 6 }
→ 200 { "chunks": [ { "document_id","content","score","metadata" } ] }
```

### 4.7 Agents (`/agents`)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/agents` | cria agente (type, persona, prompt, model) |
| GET | `/agents` | lista agentes do workspace |
| GET | `/agents/{id}` | detalhe (tools, permissões, memória resumida) |
| PATCH | `/agents/{id}` | reconfigura |
| PUT | `/agents/{id}/tools` | define tools habilitadas |
| PUT | `/agents/{id}/permissions` | define escopos + requires_approval |
| POST | `/agents/{id}/execute` | dispara execução ad-hoc (202 → run_id) |
| GET | `/agents/{id}/runs` | histórico de execuções (tokens, custo) |
| GET | `/runs/{id}` | detalhe de uma execução + steps |
| POST | `/runs/{id}/cancel` | cancela execução |

### 4.8 Approvals (`/approvals`)

| Método | Rota | Papel | Descrição |
|--------|------|-------|-----------|
| GET | `/approvals` | manager+ | pendentes (filtros: status, action) |
| GET | `/approvals/{id}` | manager+ | detalhe + payload da ação |
| POST | `/approvals/{id}/approve` | manager+ | aprova → executa ação |
| POST | `/approvals/{id}/reject` | manager+ | rejeita (com motivo) |

### 4.9 Office (`/office`)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/office/scene` | cena atual (grid, móveis, avatares) |
| GET | `/office/furniture-catalog` | catálogo global de móveis |
| POST | `/office/furniture` | posiciona móvel (admin/manager) |
| PATCH | `/office/furniture/{id}` | move/rotaciona |
| DELETE | `/office/furniture/{id}` | remove |
| GET | `/office/avatars/me` | meu hamster |
| PUT | `/office/avatars/{id}/appearance` | customiza aparência |

> Movimentação de avatares e presença NÃO usam REST — são eventos WebSocket (ver doc 05).

### 4.10 Audit & Billing (`/audit`)

| Método | Rota | Papel | Descrição |
|--------|------|-------|-----------|
| GET | `/audit/events` | manager+ | consulta eventos (filtros: type, actor, período) |
| GET | `/billing/usage` | manager+ | consumo de tokens/custo por agente e período |
| GET | `/billing/usage/export` | admin | export CSV |

### 4.11 Notifications (`/notifications`)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/notifications` | lista (não lidas primeiro) |
| POST | `/notifications/{id}/read` | marca lida |
| POST | `/notifications/read-all` | marca todas |

### 4.12 Health & Meta

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/healthz` | liveness |
| GET | `/readyz` | readiness (DB, Redis, Ollama, MinIO) |
| GET | `/api/v1/openapi.json` | contrato OpenAPI (gerado pelo FastAPI) |

## 5. Observações de implementação

- **OpenAPI** gerado automaticamente pelo FastAPI; usado para gerar o cliente TypeScript do frontend (`openapi-typescript`).
- Schemas de request/response são **Pydantic v2** (`*Create`, `*Update`, `*Read`).
- Uploads grandes: padrão **presigned URL** direto ao MinIO; backend só registra metadados e enfileira indexação — a API nunca faz streaming do binário.
- Endpoints que disparam trabalho de IA retornam **202 Accepted** com `run_id`; o resultado chega via WebSocket e fica consultável em `/runs/{id}`.
