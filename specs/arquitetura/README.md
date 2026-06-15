# Arquitetura — Hamster Office

Arquitetura completa do sistema, elaborada a partir dos specs de produto em [`../`](../).
**Hamster Office** é um SaaS multi-tenant: um escritório virtual estilo Habbo onde humanos e
agentes de IA (hamsters) colaboram em projetos, tarefas, chats e conhecimento.

## Índice

| # | Documento | Conteúdo |
|---|-----------|----------|
| 00 | [Visão Geral](./00-visao-geral.md) | Princípios, stack, **C4 Contexto e Contêiner**, fluxos-chave, NFRs, ADRs |
| 01 | [Domínio](./01-dominio.md) | Bounded contexts, linguagem ubíqua, agregados, eventos, **C4 Componentes** |
| 02 | [Entidades](./02-entidades.md) | Entidades detalhadas por contexto e enums |
| — | [Banco de Dados](../banco-de-dados.md) | Schema PostgreSQL + pgvector, **RLS**, índices, migrations |
| 04 | [APIs REST](./04-apis-rest.md) | Contratos HTTP por módulo, RBAC, paginação, erros |
| 05 | [WebSockets](./05-websockets.md) | Realtime: chat, presença, escritório, streaming de agentes |
| 06 | [Multi-Tenant](./06-multi-tenant.md) | Isolamento shared-schema + RLS, governança, billing |
| 07 | [Módulos e Estrutura](./07-modulos-e-estrutura.md) | Arquitetura hexagonal, monorepo, árvore de diretórios |
| 08 | [Agentes de IA](./08-agentes-ia.md) | Orquestração, tools, memória, RAG, aprovação humana |
| 09 | [Roadmap](./09-roadmap.md) | Implementação em sprints até o MVP e além |

## Resumo executivo das decisões

| Decisão | Escolha |
|---------|---------|
| Estilo arquitetural | **Modular Monolith** + arquitetura hexagonal por módulo (DDD) |
| Multi-tenancy | **Shared-schema + `workspace_id` + Row-Level Security** (caminho p/ schema/DB-per-tenant) |
| Backend | FastAPI (Python 3.12), Pydantic v2 |
| Frontend | Next.js + TypeScript; escritório em **PixiJS (2.5D isométrico)** |
| Banco | PostgreSQL 16 + pgvector (HNSW cosine) |
| Realtime | WebSocket único multiplexado + **Redis pub/sub** (fan-out multi-réplica) |
| Filas/Workers | **arq** (asyncio sobre Redis) |
| IA | Ollama + Qwen3 8B; especialização por **configuração** (prompt + tools + permissões + memória) |
| Storage | MinIO (S3), presigned URLs, prefixo por tenant |
| Governança | Outbox de eventos, auditoria append-only, custo/tokens por agente, human-in-the-loop |

## Como ler

1. Comece por **00 (Visão Geral)** para o panorama e os diagramas C4.
2. **01–02 + Banco de Dados** para o modelo de domínio e persistência.
3. **04–05** para as interfaces (REST e WS).
4. **06–08** para as decisões transversais (tenancy, estrutura, IA).
5. **09** para o plano de execução.

> Os ADRs completos devem morar em `docs/decisions/`. Diagramas usam Mermaid (renderizam no GitHub/VS Code).
