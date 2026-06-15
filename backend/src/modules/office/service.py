"""Presença/movimentação no escritório — estado efêmero em Redis (TTL + pub/sub).

Posições não são persistidas no PostgreSQL (alta frequência). Cada avatar online vive em
`presence:{workspace}:{scene}` (hash) com TTL renovado por heartbeat/movimento.
"""

import json

from ...core.redis import get_redis

PRESENCE_TTL = 120  # segundos


def _key(workspace_id: str, scene_id: str) -> str:
    return f"presence:{workspace_id}:{scene_id}"


async def set_presence(workspace_id: str, scene_id: str, avatar_id: str, data: dict) -> None:
    r = get_redis()
    key = _key(workspace_id, scene_id)
    await r.hset(key, avatar_id, json.dumps(data))
    await r.expire(key, PRESENCE_TTL)


async def remove_presence(workspace_id: str, scene_id: str, avatar_id: str) -> None:
    await get_redis().hdel(_key(workspace_id, scene_id), avatar_id)


async def get_presence(workspace_id: str, scene_id: str) -> list[dict]:
    raw = await get_redis().hgetall(_key(workspace_id, scene_id))
    out = []
    for avatar_id, payload in raw.items():
        try:
            d = json.loads(payload)
            d["avatar_id"] = avatar_id
            out.append(d)
        except json.JSONDecodeError:
            continue
    return out
