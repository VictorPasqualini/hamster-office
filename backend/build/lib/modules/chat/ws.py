"""Gateway WebSocket multiplexado: /ws?token=...&workspace_id=...

Comandos cliente→servidor (JSON): subscribe, unsubscribe, message.send, ping.
Eventos servidor→cliente são entregues pelo ConnectionManager via Redis pub/sub.
"""

import json
import logging

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from ...core.database import session_scope
from ...core.realtime import manager
from ...core.security import decode_token
from ...db.models import Membership, Room
from .service import handle_user_message

log = logging.getLogger("ws")
ws_router = APIRouter()


async def _authenticate(token: str, workspace_id: str) -> str | None:
    """Retorna membership_id se o token é válido e o usuário pertence ao workspace."""
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    async with session_scope() as db:
        m = await db.scalar(
            select(Membership).where(
                Membership.user_id == payload["sub"],
                Membership.workspace_id == workspace_id,
                Membership.status == "active",
            )
        )
        return str(m.id) if m else None


@ws_router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = "", workspace_id: str = ""):
    membership_id = await _authenticate(token, workspace_id)
    if not membership_id:
        await ws.close(code=4401)
        return
    await ws.accept()
    await ws.send_text(json.dumps({"type": "connected", "data": {"workspace_id": workspace_id}}))

    try:
        while True:
            raw = await ws.receive_text()
            try:
                cmd = json.loads(raw)
            except json.JSONDecodeError:
                continue
            op = cmd.get("op")

            if op == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

            elif op == "subscribe":
                channel = cmd.get("channel", "")
                if _authorized_channel(channel, workspace_id):
                    await manager.subscribe(ws, channel)
                    await ws.send_text(
                        json.dumps({"type": "subscribed", "channel": channel})
                    )

            elif op == "unsubscribe":
                await manager.unsubscribe(ws, cmd.get("channel"))

            elif op == "message.send":
                channel = cmd.get("channel", "")
                room_id = channel.removeprefix("room:")
                content = (cmd.get("data") or {}).get("content", "").strip()
                if room_id and content:
                    async with session_scope(workspace_id=workspace_id) as db:
                        room = await db.scalar(select(Room).where(Room.id == room_id))
                        if room:
                            await handle_user_message(
                                db,
                                workspace_id=workspace_id,
                                room_id=room_id,
                                author_id=membership_id,
                                content=content,
                            )
                    await ws.send_text(
                        json.dumps({"type": "ack", "client_msg_id": cmd.get("client_msg_id")})
                    )
    except WebSocketDisconnect:
        await manager.unsubscribe(ws)
    except Exception as e:  # noqa: BLE001
        log.warning("WS erro: %s", e)
        await manager.unsubscribe(ws)


def _authorized_channel(channel: str, workspace_id: str) -> bool:
    # MVP: canais permitidos por prefixo. Validação fina de pertencimento pode ser adicionada.
    return channel.startswith(("room:", "run:", f"workspace:{workspace_id}", "user:"))
