# Estratégia Multi-Tenant

> Como o Hamster Office isola dados, recursos e custos entre workspaces (tenants).

## 1. Modelo escolhido: shared-schema + Row-Level Security

**Decisão (ADR-0002):** banco único, schema único por bounded context, **discriminador `workspace_id`**
em toda tabela de negócio, com **Row-Level Security (RLS)** do PostgreSQL como rede de segurança.

### Comparação dos modelos

| Modelo | Isolamento | Custo operacional | Escala de tenants | Veredito |
|--------|-----------|-------------------|-------------------|----------|
| Database-per-tenant | Máximo | Alto (migrations × N, conexões) | Baixo/médio | ❌ overkill no início |
| Schema-per-tenant | Alto | Médio-alto (migrations × N) | Médio | ➖ futuro enterprise |
| **Shared schema + `workspace_id` + RLS** | Bom (defense-in-depth) | Baixo | Alto | ✅ **escolhido** |

**Por quê:** o produto é SaaS com muitos tenants pequenos/médios; shared-schema dá o melhor
custo-benview de operação e escala. RLS elimina o risco de "esqueci o `WHERE workspace_id`".
Para clientes enterprise que exijam isolamento físico, há um **caminho de promoção** (seção 7).

## 2. Defense-in-depth: três camadas de isolamento

```
1. Aplicação   →  resolve tenant, RBAC, escopo do recurso
2. Repositório →  todas as queries carregam workspace_id (explícito)
3. Banco (RLS) →  política força workspace_id = current_workspace_id()  ← rede de segurança
```

Nenhuma camada confia cegamente na anterior. Mesmo um bug na aplicação (query sem filtro) é
barrado pela RLS, que retorna zero linhas fora do tenant atual.

## 3. Resolução do tenant (request lifecycle)

```mermaid
sequenceDiagram
  participant C as Cliente
  participant MW as Tenant Middleware
  participant DB as PostgreSQL (pool)
  C->>MW: request + JWT (claim workspace_id) / slug
  MW->>MW: valida membership ativa do user no workspace
  MW->>DB: BEGIN; SELECT set_config('app.workspace_id', :wid, true)
  MW->>DB: ...queries do caso de uso (RLS ativa)...
  MW->>DB: COMMIT
  MW-->>C: resposta
```

- O `workspace_id` vem do **claim do JWT** (escolhido no login/troca de workspace), não de input arbitrário do corpo.
- `set_config(..., true)` é **transação-local** — não vaza entre requisições que reusam a conexão do pool.
- Trocar de workspace = novo access token com outro `workspace_id` (endpoint `/auth/switch-workspace`).

## 4. RLS na prática

```sql
-- Roles
CREATE ROLE app_rw       NOLOGIN NOSUPERUSER;            -- aplicação (sofre RLS)
CREATE ROLE app_worker   NOLOGIN NOSUPERUSER;            -- workers (sofrem RLS)
CREATE ROLE app_migrator NOLOGIN NOSUPERUSER BYPASSRLS;  -- migrations/jobs cross-tenant

-- Política padrão (toda tabela com workspace_id)
ALTER TABLE chat.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat.messages FORCE  ROW LEVEL SECURITY;     -- vale até para o owner da tabela
CREATE POLICY tenant_isolation ON chat.messages
  USING       (workspace_id = current_workspace_id())
  WITH CHECK  (workspace_id = current_workspace_id());
```

**Pontos de atenção:**
- A role da aplicação **não** pode ser superuser nem owner sem `FORCE` — superuser ignora RLS.
- `current_workspace_id()` retorna `NULL` se não setado → políticas negam tudo (fail-safe).
- Tabelas **globais** (`auth.users`, `office.furniture_catalog`) não têm RLS de tenant.
- `workspace.workspaces` usa política especial: visível se existe membership ativa do usuário.

## 5. Isolamento nos demais recursos

| Recurso | Isolamento |
|---------|-----------|
| **PostgreSQL** | RLS por `workspace_id` (acima) |
| **pgvector / RAG** | Busca vetorial roda sob RLS → nunca retorna chunks de outro tenant |
| **Redis** | Namespacing por chave: `ws:{id}:presence`, canais `room:{id}` validados contra o tenant |
| **MinIO** | Prefixo por tenant: `s3://hamster/{workspace_id}/documents/...`; URLs assinadas com escopo |
| **WebSocket** | Subscribe autorizado só a canais do workspace do JWT |
| **Filas (arq)** | Todo job carrega `workspace_id`; o worker faz `set_config` antes de tocar o banco |
| **Ollama** | Stateless; o isolamento está no contexto/prompt montado a partir de dados já filtrados |
| **Logs/Tracing** | `workspace_id` em todo span/log para correlação e filtragem |

## 6. Governança por tenant

| Dimensão | Mecanismo |
|----------|-----------|
| **Custo & tokens** | `agents.agent_runs` + materialização `audit.usage_daily` por workspace/agente |
| **Cotas** | `workspace.settings.monthly_token_budget`; worker recusa/avisa ao exceder |
| **Rate limit** | Buckets por `workspace_id` (e por usuário) no Redis |
| **Planos** | `workspaces.plan` (free/pro/enterprise) governa limites de membros, storage, agentes |
| **Auditoria** | `audit.audit_log` particionada, filtrável por tenant; retenção por plano |
| **Backup/restore** | Lógico global; restore seletivo por `workspace_id` quando necessário |

## 7. Caminho de promoção para isolamento físico (enterprise)

Quando um cliente exigir isolamento mais forte, sem reescrever o código:

1. **Schema-per-tenant** — mesmo código, `search_path` por tenant; migrations replicadas por schema.
2. **Database/instância dedicada** — roteamento de conexão por tenant (mapa tenant→DSN); o `workspace_id`
   continua existindo, então o código não muda.
3. **Sharding por tenant** — distribuir tenants entre instâncias por hash do `workspace_id`.

A presença universal de `workspace_id` desde o dia 1 é o que torna essa migração incremental e barata.

## 8. Checklist anti-vazamento (revisão de PR)

- [ ] Tabela nova de negócio tem `workspace_id NOT NULL`?
- [ ] RLS habilitada + `FORCE` + política `tenant_isolation`?
- [ ] Nenhuma query usa role com `BYPASSRLS` fora de migrations/jobs cross-tenant?
- [ ] Chaves Redis e prefixos MinIO incluem `workspace_id`?
- [ ] Job de fila propaga e seta `app.workspace_id` antes de acessar o banco?
- [ ] Canal WebSocket valida o tenant no subscribe?
- [ ] Teste automatizado: usuário do tenant A não enxerga dado do tenant B (em REST, RAG e WS)?
