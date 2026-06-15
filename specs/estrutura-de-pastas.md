ai-office/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── types/
│   └── public/
│
├── backend/
│   ├── src/
│   │
│   ├── core/
│   │   ├── config/
│   │   ├── security/
│   │   ├── database/
│   │   ├── exceptions/
│   │   └── logging/
│   │
│   ├── modules/
│   │   ├── auth/
│   │   ├── workspace/
│   │   ├── users/
│   │   ├── projects/
│   │   ├── tasks/
│   │   ├── chat/
│   │   ├── documents/
│   │   ├── agents/
│   │   ├── knowledge/
│   │   └── notifications/
│   │
│   ├── integrations/
│   │   ├── ollama/
│   │   ├── email/
│   │   ├── postgres/
│   │   └── minio/
│   │
│   ├── workers/
│   │   ├── document_processor/
│   │   ├── embeddings/
│   │   └── scheduled_jobs/
│   │
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── projects.py
│   │   │   ├── tasks.py
│   │   │   ├── agents.py
│   │   │   └── chat.py
│   │   └── websocket/
│   │
│   └── main.py
│
├── infra/
│   ├── docker/
│   ├── nginx/
│   ├── postgres/
│   ├── minio/
│   └── ollama/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   └── decisions/
│
└── docker-compose.yml

agents/
│
├── domain/
│   ├── entities/
│   │   ├── agent.py
│   │   ├── tool.py
│   │   └── memory.py
│   │
│   └── services/
│       └── agent_executor.py
│
├── application/
│   ├── use_cases/
│   │   ├── create_agent.py
│   │   ├── execute_agent.py
│   │   └── assign_agent.py
│
├── infrastructure/
│   ├── repositories/
│   └── adapters/
│
└── presentation/
    └── controllers/
	 
integrations/
└── ollama/
    ├── client.py
    ├── models.py
    ├── embeddings.py
    ├── prompts/
    │   ├── commercial.txt
    │   ├── finance.txt
    │   ├── developer.txt
    │   └── analyst.txt
    │
    └── services/
        ├── chat_service.py
        └── embedding_service.py
		
knowledge/
│
├── domain/
│   ├── document.py
│   └── chunk.py
│
├── application/
│   ├── upload_document.py
│   ├── search_document.py
│   └── generate_embeddings.py
│
└── infrastructure/
    ├── pgvector_repository.py
    └── minio_repository.py
	
chat/
│
├── domain/
│   ├── message.py
│   ├── room.py
│   └── participant.py
│
├── application/
│   ├── send_message.py
│   ├── create_room.py
│   └── add_participant.py
│
└── websocket/
    ├── connection_manager.py
    └── handlers.py