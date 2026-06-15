"""Gateway WebSocket multiplexado: /ws?token=...&workspace_id=...

Comandos cliente→servidor (JSON): subscribe, unsubscribe, message.send,
presence.enter, presence.move, ping.
Eventos servidor→cliente chegam pelo ConnectionManager via Redis pub/sub.
"""

import json
import logging

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from ...core.database import session_scope
from ...core.realtime import manager, publish_event
from ...core.security import decode_token
from ...db.models import Membership, Room
from ..office.service import get_presence, remove_presence, set_presence
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

    # presença ativa desta conexão: {scene_id, avatar_id}
    presence: dict[str, str] = {}

    try:
        while True:
            raw = await ws.receive_text()
            try:
                cmd = json.loads(raw)
            except json.JSONDecodeError:
                continue
            op = cmd.get("op")
            data = cmd.get("data") or {}

            if op == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

            elif op == "subscribe":
                channel = cmd.get("channel", "")
                if _authorized_channel(channel, workspace_id):
                    await manager.subscribe(ws, channel)
                    await ws.send_text(json.dumps({"type": "subscribed", "channel": channel}))
                    # snapshot de presença ao entrar num canal de escritório
                    if channel.startswith("office:"):
                        scene_id = channel.removeprefix("office:")
                        snap = await get_presence(workspace_id, scene_id)
                        await ws.send_text(
                            json.dumps(
                                {
                                    "type": "office.presence.snapshot",
                                    "channel": channel,
                                    "data": {"avatars": snap},
                                }
                            )
                        )

            elif op == "unsubscribe":
                await manager.unsubscribe(ws, cmd.get("channel"))

            elif op == "message.send":
                channel = cmd.get("channel", "")
                room_id = channel.removeprefix("room:")
                content = data.get("content", "").strip()
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

            elif op in ("presence.enter", "presence.move"):
                scene_id = str(data.get("scene_id", ""))
                avatar_id = str(data.get("avatar_id", ""))
                if not scene_id or not avatar_id:
                    continue
                payload = {
                    "x": int(data.get("x", 0)),
                    "y": int(data.get("y", 0)),
                    "facing": data.get("facing", "down"),
                    "status": data.get("status", "online"),
                    "name": data.get("name", ""),
                    "color": data.get("color", "gray"),
                    "kind": data.get("kind", "user"),
                }
                await set_presence(workspace_id, scene_id, avatar_id, payload)
                presence = {"scene_id": scene_id, "avatar_id": avatar_id}
                evt = "office.avatar.entered" if op == "presence.enter" else "office.avatar.moved"
                await publish_event(f"office:{scene_id}", evt, {"avatar_id": avatar_id, **payload})

    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        log.warning("WS erro: %s", e)
    finally:
        if presence:
            await remove_presence(workspace_id, presence["scene_id"], presence["avatar_id"])
            await publish_event(
                f"office:{presence['scene_id']}",
                "office.avatar.left",
                {"avatar_id": presence["avatar_id"]},
            )
        await manager.unsubscribe(ws)


def _authorized_channel(channel: str, workspace_id: str) -> bool:
    # MVP: canais permitidos por prefixo. Validação fina de pertencimento pode ser adicionada.
    return channel.startswith(("room:", "run:", "office:", f"workspace:{workspace_id}", "user:"))
