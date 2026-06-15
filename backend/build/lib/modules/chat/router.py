from fastapi import APIRouter, Depends
from sqlalchemy import select

from ...core.deps import TenantCtx, tenant_ctx
from ...core.exceptions import NotFound
from ...db.models import Message, Participant, Room
from .schemas import MessageSend, RoomCreate, RoomOut
from .service import handle_user_message, msg_dict

router = APIRouter(prefix="/rooms", tags=["chat"])


def _out(r: Room) -> RoomOut:
    return RoomOut(
        id=str(r.id),
        type=r.type,
        name=r.name,
        topic=r.topic,
        project_id=str(r.project_id) if r.project_id else None,
    )


@router.post("", response_model=RoomOut, status_code=201)
async def create_room(body: RoomCreate, ctx: TenantCtx = Depends(tenant_ctx)):
    r = Room(
        workspace_id=ctx.workspace_id,
        project_id=body.project_id,
        type=body.type,
        name=body.name,
        topic=body.topic,
        created_by=ctx.membership_id,
    )
    ctx.db.add(r)
    await ctx.db.flush()
    # criador entra como owner
    ctx.db.add(
        Participant(
            room_id=r.id,
            member_kind="user",
            member_id=ctx.membership_id,
            workspace_id=ctx.workspace_id,
            role="owner",
        )
    )
    for aid in body.agent_ids:
        ctx.db.add(
            Participant(
                room_id=r.id,
                member_kind="agent",
                member_id=aid,
                workspace_id=ctx.workspace_id,
            )
        )
    return _out(r)


@router.get("", response_model=list[RoomOut])
async def list_rooms(ctx: TenantCtx = Depends(tenant_ctx)):
    rows = await ctx.db.scalars(select(Room).order_by(Room.created_at))
    return [_out(r) for r in rows]


@router.get("/{room_id}/messages")
async def list_messages(
    room_id: str, limit: int = 50, ctx: TenantCtx = Depends(tenant_ctx)
):
    rows = await ctx.db.scalars(
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(min(limit, 200))
    )
    items = [msg_dict(m) for m in rows]
    items.reverse()
    return {"items": items}


@router.post("/{room_id}/messages", status_code=201)
async def send_message(room_id: str, body: MessageSend, ctx: TenantCtx = Depends(tenant_ctx)):
    """Envio via HTTP (fallback do WebSocket). Dispara agentes mencionados."""
    room = await ctx.db.scalar(select(Room).where(Room.id == room_id))
    if not room:
        raise NotFound("Sala não encontrada")
    m = await handle_user_message(
        ctx.db,
        workspace_id=ctx.workspace_id,
        room_id=room_id,
        author_id=ctx.membership_id,
        content=body.content,
        parent_id=body.parent_id,
    )
    return msg_dict(m)
