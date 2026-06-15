"""Seed de dados demo: workspace, admin, projeto, agentes especializados e sala de chat.

Idempotente: se o workspace 'acme' já existe, não faz nada.
"""

import logging

from sqlalchemy import select

from .core.database import session_scope
from .core.security import hash_password
from .db.models import (
    Agent,
    Membership,
    Message,
    Participant,
    Project,
    ProjectAgent,
    ProjectMember,
    Room,
    User,
    Workspace,
    WorkspaceSettings,
)

log = logging.getLogger("seed")

DEMO_EMAIL = "ana@acme.com"
DEMO_PASSWORD = "hamster123"
DEMO_SLUG = "acme"

AGENT_SEEDS = [
    {
        "type": "commercial",
        "name": "Vendinha",
        "persona": "Agente comercial focado em propostas e relacionamento com clientes.",
        "system_prompt": (
            "Você é o agente Comercial da empresa. Ajude com propostas, follow-ups e "
            "qualificação de leads. Consulte a base de conhecimento quando precisar de dados. "
            "Seja objetivo e proativo, sugira próximos passos e crie tarefas quando fizer sentido."
        ),
        "tools": ["search_kb", "create_task", "post_message"],
        "appearance": {"color": "orange"},
    },
    {
        "type": "finance",
        "name": "Centavo",
        "persona": "Agente financeiro: fluxo de caixa, faturamento e análises.",
        "system_prompt": (
            "Você é o agente Financeiro. Responda sobre finanças, custos e faturamento com base "
            "nos documentos do workspace. Ações financeiras críticas exigem aprovação humana."
        ),
        "tools": ["search_kb", "create_task"],
        "appearance": {"color": "green"},
    },
    {
        "type": "developer",
        "name": "Bitzão",
        "persona": "Agente desenvolvedor: tarefas técnicas e documentação.",
        "system_prompt": (
            "Você é o agente Desenvolvedor. Ajude com decisões técnicas, quebra de tarefas e "
            "documentação. Crie e atualize tarefas técnicas no projeto quando solicitado."
        ),
        "tools": ["search_kb", "create_task", "update_task", "post_message"],
        "appearance": {"color": "blue"},
    },
    {
        "type": "support",
        "name": "Fofuxo",
        "persona": "Agente de atendimento ao cliente.",
        "system_prompt": (
            "Você é o agente de Atendimento. Responda dúvidas com empatia e clareza usando a base "
            "de conhecimento. Encaminhe para humanos quando necessário e registre tarefas de follow-up."
        ),
        "tools": ["search_kb", "post_message", "create_task"],
        "appearance": {"color": "pink"},
    },
]


async def seed_demo() -> None:
    # 1) Usuário + workspace + membership (tabelas sem RLS de tenant)
    async with session_scope() as db:
        existing = await db.scalar(select(Workspace).where(Workspace.slug == DEMO_SLUG))
        if existing:
            log.info("Seed já aplicado (workspace '%s' existe).", DEMO_SLUG)
            return

        user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if not user:
            user = User(
                email=DEMO_EMAIL,
                name="Ana Admin",
                password_hash=hash_password(DEMO_PASSWORD),
            )
            db.add(user)
            await db.flush()

        ws = Workspace(slug=DEMO_SLUG, name="ACME Ltda", owner_user_id=user.id, plan="pro")
        db.add(ws)
        await db.flush()
        db.add(WorkspaceSettings(workspace_id=ws.id))
        membership = Membership(
            workspace_id=ws.id, user_id=user.id, role="admin", status="active"
        )
        db.add(membership)
        await db.flush()
        ws_id = ws.id
        membership_id = membership.id

    # 2) Conteúdo de tenant (com contexto RLS)
    async with session_scope(workspace_id=str(ws_id)) as db:
        project = Project(
            workspace_id=ws_id,
            name="Onboarding ACME",
            client_name="ACME Ltda",
            description="Projeto inicial de demonstração.",
            owner_membership_id=membership_id,
        )
        db.add(project)
        await db.flush()
        db.add(
            ProjectMember(
                project_id=project.id,
                membership_id=membership_id,
                workspace_id=ws_id,
                project_role="lead",
            )
        )

        agent_ids = []
        for spec in AGENT_SEEDS:
            agent = Agent(workspace_id=ws_id, **spec)
            db.add(agent)
            await db.flush()
            agent_ids.append(agent.id)
            db.add(ProjectAgent(project_id=project.id, agent_id=agent.id, workspace_id=ws_id))

        room = Room(
            workspace_id=ws_id,
            project_id=project.id,
            type="public_channel",
            name="geral",
            topic="Canal geral do projeto",
            created_by=membership_id,
        )
        db.add(room)
        await db.flush()
        db.add(
            Participant(
                room_id=room.id,
                member_kind="user",
                member_id=membership_id,
                workspace_id=ws_id,
                role="owner",
            )
        )
        for aid in agent_ids:
            db.add(
                Participant(
                    room_id=room.id, member_kind="agent", member_id=aid, workspace_id=ws_id
                )
            )
        db.add(
            Message(
                workspace_id=ws_id,
                room_id=room.id,
                author_kind="system",
                content="Bem-vindo ao Hamster Office! Mencione um agente com @Nome para começar.",
            )
        )

    log.info("Seed demo criado: login %s / %s (workspace '%s').", DEMO_EMAIL, DEMO_PASSWORD, DEMO_SLUG)
