# Entidades do Domínio

> Descrição lógica das entidades por bounded context. O mapeamento físico (tipos SQL,
> índices, RLS) está em [banco-de-dados.md](../banco-de-dados.md).
> Convenções: todo agregado de negócio tem `id (UUID)`, `workspace_id (UUID)` (exceto IAM global),
> `created_at`, `updated_at`. Soft-delete via `deleted_at` onde indicado.

## Tipos enumerados (compartilhados)

```text
Role          = admin | manager | collaborator | guest
MemberStatus  = invited | active | suspended | removed
ProjectStatus = active | paused | archived
TaskStatus    = backlog | todo | in_progress | review | blocked | done | canceled
Priority      = low | medium | high | urgent
RoomType      = public_channel | private_channel | direct | human_agent
AuthorKind    = user | agent | system
AgentType     = commercial | finance | legal | data_analyst | developer | support | custom
RunStatus     = queued | running | waiting_approval | completed | failed | canceled
DocStatus     = uploaded | processing | indexed | failed
ApprovalStatus= pending | approved | rejected | expired
ApprovalAction= send_email | sign_document | financial_op | delete_data | external_api | custom
NotifChannel  = in_app | email
EmbeddingDim  = 1024   # Qwen3 embeddings (ajustar ao modelo real)
```

---

## 1. Identity & Access (schema `auth`)

### User (global, fora do tenant)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| email | citext | único global |
| name | text | |
| avatar_url | text | foto real (opcional) |
| password_hash | text | Argon2id |
| is_active | bool | |
| last_login_at | timestamptz | |

### RefreshToken
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK User |
| token_hash | text | hash do refresh |
| expires_at | timestamptz | |
| revoked_at | timestamptz | rotação |
| user_agent / ip | text | auditoria de sessão |

> Permissões/papéis NÃO ficam aqui — são por **workspace** (ver Membership). Um usuário pode ser
> `admin` em um workspace e `guest` em outro.

---

## 2. Workspace (schema `workspace`)

### Workspace (raiz de tenant)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK = tenant id |
| slug | citext | único global (subdomínio/rota) |
| name | text | |
| plan | text | free \| pro \| enterprise |
| owner_user_id | UUID | criador |
| status | text | active \| suspended |

### WorkspaceSettings
| Campo | Tipo | Notas |
|-------|------|-------|
| workspace_id | UUID | PK/FK |
| default_model | text | ex.: `qwen3:8b` |
| allowed_agent_tools | text[] | tools liberadas no tenant |
| monthly_token_budget | bigint | limite de consumo |
| office_theme | text | tema visual do escritório |

### Membership
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| user_id | UUID | FK User |
| role | Role | |
| status | MemberStatus | |
| invited_by | UUID | |
| **único** | (workspace_id, user_id) | |

### Invite
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| email | citext | convidado |
| role | Role | papel proposto |
| token | text | link de convite |
| expires_at | timestamptz | |
| accepted_at | timestamptz | |

---

## 3. Projects (schema `projects`)

### Project
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| name | text | |
| client_name | text | cliente do projeto |
| description | text | |
| status | ProjectStatus | |
| owner_membership_id | UUID | responsável |

### ProjectMember
| Campo | Tipo | Notas |
|-------|------|-------|
| project_id | UUID | FK |
| membership_id | UUID | FK Membership |
| project_role | text | lead \| member \| viewer |
| **único** | (project_id, membership_id) | |

### ProjectAgent
| Campo | Tipo | Notas |
|-------|------|-------|
| project_id | UUID | FK |
| agent_id | UUID | FK Agent |
| **único** | (project_id, agent_id) | agentes associados ao projeto |

---

## 4. Tasks (schema `tasks`)

### Task
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| project_id | UUID | FK |
| title | text | |
| description | text | |
| status | TaskStatus | |
| priority | Priority | |
| due_date | timestamptz | |
| assignee_kind | AuthorKind | user \| agent |
| assignee_id | UUID | membership_id ou agent_id |
| created_by_kind | AuthorKind | quem criou (humano/agente) |
| parent_task_id | UUID | subtarefa (self-FK) |
| order | int | ordenação em board |

### TaskComment
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| task_id | UUID | FK |
| author_kind / author_id | | autor |
| body | text | |

### TaskActivity (histórico imutável)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| task_id | UUID | FK |
| type | text | created \| status_changed \| assigned ... |
| from_value / to_value | jsonb | diff |
| actor_kind / actor_id | | |

---

## 5. Chat / Collaboration (schema `chat`)

### Room
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| project_id | UUID | FK (nullable — canais globais do workspace) |
| type | RoomType | |
| name | text | null em DMs |
| topic | text | |
| created_by | UUID | membership |

### Participant
| Campo | Tipo | Notas |
|-------|------|-------|
| room_id | UUID | FK |
| member_kind | AuthorKind | user \| agent |
| member_id | UUID | membership_id ou agent_id |
| role | text | owner \| member |
| muted | bool | |
| last_read_message_id | UUID | read receipt |

### Message
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK (ULID-friendly p/ ordenação) |
| room_id | UUID | FK |
| author_kind / author_id | | user \| agent \| system |
| content | text | markdown |
| parent_id | UUID | thread/resposta |
| agent_run_id | UUID | se gerada por agente |
| edited_at | timestamptz | |
| mentions | jsonb | [{kind,id}] |

### Attachment
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| message_id | UUID | FK |
| document_id | UUID | FK Document (se for da base) |
| object_key | text | MinIO key |
| filename / mime / size | | |

### Reaction
| Campo | Tipo | Notas |
|-------|------|-------|
| message_id / member_id / emoji | | PK composto |

---

## 6. Office — escritório espacial (schema `office`)

### OfficeScene
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK (1 cena principal por workspace; salas extras possíveis) |
| name | text | |
| grid_width / grid_height | int | dimensões isométricas |
| theme | text | tema visual |
| layout | jsonb | metadados de pisos/paredes/zonas |

### FurnitureCatalog (global, sem tenant)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| code | text | ex.: `desk_wood` |
| name | text | |
| footprint | jsonb | células ocupadas |
| sprite_url | text | asset |
| category | text | mesa \| planta \| parede \| sala_reuniao ... |

### FurniturePlacement
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| scene_id | UUID | FK |
| furniture_code | text | FK Catalog |
| x / y | int | célula |
| rotation | int | 0/90/180/270 |
| z_index | int | empilhamento |

### Avatar (Hamster)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| owner_kind | AuthorKind | user \| agent |
| owner_id | UUID | membership_id ou agent_id |
| appearance | jsonb | cor, roupa, acessórios (customização tipo jogo) |
| home_x / home_y | int | posição padrão (mesa) |

### AvatarState (efêmero — Redis primário, persistência opcional)
| Campo | Tipo | Notas |
|-------|------|-------|
| avatar_id | UUID | |
| scene_id | UUID | |
| x / y / facing | | posição/direção atuais |
| status | text | online \| busy \| away \| offline |
| updated_at | | |

> **Decisão**: presença e movimentação vivem em Redis (TTL + pub/sub), não no Postgres, por serem
> alta frequência e efêmeros. Só persistimos `Avatar` (customização) e `FurniturePlacement` (layout).

---

## 7. Agents (schema `agents`)

### Agent
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| type | AgentType | |
| name | text | ex.: "FinanceBot" |
| persona | text | descrição pública |
| system_prompt | text | prompt de especialização |
| model | text | default `qwen3:8b` |
| temperature | numeric | |
| is_active | bool | |
| avatar_id | UUID | FK Avatar (hamster do agente) |

### AgentTool
| Campo | Tipo | Notas |
|-------|------|-------|
| agent_id | UUID | FK |
| tool_code | text | ex.: `create_task`, `search_kb`, `send_email` |
| config | jsonb | parâmetros (escopo, limites) |
| **único** | (agent_id, tool_code) | |

### AgentPermission
| Campo | Tipo | Notas |
|-------|------|-------|
| agent_id | UUID | FK |
| scope | text | ex.: `tasks:write`, `documents:read`, `email:send` |
| requires_approval | bool | ação crítica? |

### AgentMemory (longo prazo, vetorial)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| agent_id | UUID | FK |
| project_id | UUID | FK (nullable) |
| kind | text | fact \| summary \| preference |
| content | text | |
| embedding | vector(1024) | pgvector |
| importance | numeric | decaimento/relevância |

### AgentRun (execução — custo/tokens)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| agent_id | UUID | FK |
| project_id | UUID | FK (nullable) |
| trigger_kind | text | chat_mention \| task \| schedule \| api |
| trigger_ref | UUID | mensagem/tarefa de origem |
| status | RunStatus | |
| model | text | |
| prompt_tokens | int | |
| completion_tokens | int | |
| total_tokens | int | (gerado) |
| cost_usd | numeric(12,6) | tokens × preço do modelo |
| latency_ms | int | |
| error | text | se falhou |

### RunStep / ToolCall
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| run_id | UUID | FK |
| seq | int | ordem |
| type | text | think \| tool_call \| tool_result \| message |
| tool_code | text | se tool_call |
| input / output | jsonb | |
| approval_request_id | UUID | se exigiu aprovação |

---

## 8. Knowledge / RAG (schema `knowledge`)

### Document
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| project_id | UUID | FK (nullable) |
| title | text | |
| object_key | text | MinIO key (arquivo original) |
| mime | text | |
| size_bytes | bigint | |
| status | DocStatus | |
| uploaded_by | UUID | membership |
| current_version | int | |

### DocumentVersion
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| document_id | UUID | FK |
| version | int | |
| object_key | text | snapshot |
| checksum | text | sha256 |

### Chunk
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| document_id | UUID | FK |
| version | int | |
| ord | int | ordem no documento |
| content | text | texto do fragmento |
| token_count | int | |
| embedding | vector(1024) | pgvector (índice HNSW) |
| metadata | jsonb | página, seção... |

---

## 9. Approvals (schema `approvals`)

### ApprovalRequest
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| agent_run_id | UUID | FK (origem) |
| action | ApprovalAction | |
| payload | jsonb | dados da ação (ex.: email destino/corpo) |
| status | ApprovalStatus | |
| requested_by_agent_id | UUID | |
| expires_at | timestamptz | |

### ApprovalDecision
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| approval_request_id | UUID | FK |
| decided_by | UUID | membership (com permissão) |
| decision | text | approved \| rejected |
| reason | text | |
| decided_at | timestamptz | |

---

## 10. Audit & Billing (schema `audit`)

### AuditEvent (append-only)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK (nullable p/ eventos globais) |
| type | text | ex.: `task.status_changed` |
| actor_kind / actor_id | | quem fez |
| target_kind / target_id | | sobre o quê |
| payload | jsonb | diff/contexto |
| trace_id | UUID | correlação |
| occurred_at | timestamptz | |

### Outbox (entrega confiável de eventos)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| aggregate | text | |
| type | text | |
| payload | jsonb | envelope do evento |
| status | text | pending \| published |
| published_at | timestamptz | |

### UsageDaily (agregado de billing — materializado)
| Campo | Tipo | Notas |
|-------|------|-------|
| workspace_id / day | | PK |
| agent_id | UUID | |
| total_tokens | bigint | |
| total_cost_usd | numeric | |
| run_count | int | |

---

## 11. Notifications (schema `notifications`)

### Notification
| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK |
| recipient_membership_id | UUID | FK |
| type | text | mention \| approval_request \| task_assigned ... |
| title / body | text | |
| link | text | deep link |
| channel | NotifChannel | |
| dedup_key | text | idempotência |
| read_at | timestamptz | |
