"""Gateway WebSocket: ConnectionManager local + fan-out via Redis pub/sub.

Cada réplica da API assina os canais Redis dos seus clientes. Ao publicar um evento
(por API ou worker), todas as réplicas com inscritos entregam aos sockets locais.
"""

import asyncio
import json
import logging

from fastapi import WebSocket
from redis.asyncio import Redis

from .redis import get_redis

log = logging.getLogger("realtime")


class ConnectionManager:
    def __init__(self) -> None:
        # channel -> set[WebSocket]
        self._channels: dict[str, set[WebSocket]] = {}
        self._pubsub_task: asyncio.Task | None = None
        self._redis: Redis | None = None

    async def start(self) -> None:
        self._redis = get_redis()
        self._pubsub_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        if self._pubsub_task:
            self._pubsub_task.cancel()

    async def subscribe(self, ws: WebSocket, channel: str) -> None:
        self._channels.setdefault(channel, set()).add(ws)

    async def unsubscribe(self, ws: WebSocket, channel: str | None = None) -> None:
        targets = [channel] if channel else list(self._channels.keys())
        for ch in targets:
            self._channels.get(ch, set()).discard(ws)

    def channels_of(self, ws: WebSocket) -> list[str]:
        return [ch for ch, subs in self._channels.items() if ws in subs]

    async def _listen(self) -> None:
        """Escuta o padrão de canais e entrega aos sockets locais inscritos."""
        assert self._redis is not None
        pubsub = self._redis.pubsub()
        await pubsub.psubscribe("rt:*")
        try:
            async for msg in pubsub.listen():
                if msg.get("type") != "pmessage":
                    continue
                channel = msg["channel"].removeprefix("rt:")
                await self._fanout(channel, msg["data"])
        except asyncio.CancelledError:
            await pubsub.close()

    async def _fanout(self, channel: str, data: str) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._channels.get(channel, set())):
            try:
                await ws.send_text(data)
            except Exception:  # noqa: BLE001 — socket morto
                dead.append(ws)
        for ws in dead:
            await self.unsubscribe(ws)


manager = ConnectionManager()


async def publish_event(channel: str, event_type: str, data: dict) -> None:
    """Publica um evento para o canal lógico (ex.: 'room:<id>')."""
    payload = json.dumps({"type": event_type, "channel": channel, "data": data}, default=str)
    await get_redis().publish(f"rt:{channel}", payload)
