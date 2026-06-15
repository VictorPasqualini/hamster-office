"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { session, wsUrl } from "./api";
import type { Message, PresenceEntry } from "./types";

interface WsEvent {
  type: string;
  channel?: string;
  data?: unknown;
}

/**
 * Conexão WebSocket por sala: assina `room:{id}`, recebe `chat.message.created`
 * em tempo real e envia mensagens via `message.send`. Reconecta com backoff.
 */
export function useRoomSocket(roomId: string | null) {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [agentBusy, setAgentBusy] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const closedRef = useRef(false);

  const channel = roomId ? `room:${roomId}` : null;

  const connect = useCallback(() => {
    const token = session.token;
    const workspaceId = session.workspaceId;
    if (!token || !workspaceId || !channel) return;

    const ws = new WebSocket(wsUrl(token, workspaceId));
    wsRef.current = ws;

    ws.onopen = () => {
      retryRef.current = 0;
      setConnected(true);
      ws.send(JSON.stringify({ op: "subscribe", channel }));
    };

    ws.onmessage = (ev) => {
      let msg: WsEvent;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      if (msg.type === "chat.message.created") {
        const m = msg.data as Message;
        setMessages((prev) => (prev.some((p) => p.id === m.id) ? prev : [...prev, m]));
        if (m.author_kind === "agent") setAgentBusy(false);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (closedRef.current) return;
      const delay = Math.min(1000 * 2 ** retryRef.current, 10000);
      retryRef.current += 1;
      setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  }, [channel]);

  useEffect(() => {
    closedRef.current = false;
    connect();
    return () => {
      closedRef.current = true;
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback(
    (content: string) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN || !channel) return false;
      ws.send(
        JSON.stringify({
          op: "message.send",
          channel,
          data: { content },
          client_msg_id: crypto.randomUUID(),
        })
      );
      if (/@\w/.test(content)) setAgentBusy(true);
      return true;
    },
    [channel]
  );

  return { connected, messages, setMessages, send, agentBusy };
}

export interface OfficeMe {
  avatar_id: string;
  name: string;
  color: string;
  kind: "user" | "agent";
  x: number;
  y: number;
}

export interface OfficeHandlers {
  onSnapshot?: (list: PresenceEntry[]) => void;
  onEnter?: (entry: PresenceEntry) => void;
  onMove?: (entry: PresenceEntry) => void;
  onLeave?: (avatarId: string) => void;
}

/**
 * Conexão WebSocket do escritório: assina `office:{sceneId}`, anuncia presença e
 * recebe movimentos dos demais avatares. Os handlers atualizam o canvas sem re-render.
 */
export function useOfficeSocket(
  sceneId: string | null,
  me: OfficeMe | null,
  handlers: OfficeHandlers
) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef(handlers);
  const meRef = useRef(me);
  const retryRef = useRef(0);
  const closedRef = useRef(false);
  handlersRef.current = handlers;
  meRef.current = me;

  const connect = useCallback(() => {
    const token = session.token;
    const workspaceId = session.workspaceId;
    if (!token || !workspaceId || !sceneId) return;

    const ws = new WebSocket(wsUrl(token, workspaceId));
    wsRef.current = ws;
    const channel = `office:${sceneId}`;

    ws.onopen = () => {
      retryRef.current = 0;
      setConnected(true);
      ws.send(JSON.stringify({ op: "subscribe", channel }));
      const m = meRef.current;
      if (m) {
        ws.send(
          JSON.stringify({
            op: "presence.enter",
            data: { scene_id: sceneId, ...m },
          })
        );
      }
    };

    ws.onmessage = (ev) => {
      let msg: { type: string; data?: unknown };
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      const h = handlersRef.current;
      const d = msg.data as PresenceEntry & { avatars?: PresenceEntry[] };
      switch (msg.type) {
        case "office.presence.snapshot":
          h.onSnapshot?.(d.avatars || []);
          break;
        case "office.avatar.entered":
          if (d.avatar_id !== meRef.current?.avatar_id) h.onEnter?.(d);
          break;
        case "office.avatar.moved":
          if (d.avatar_id !== meRef.current?.avatar_id) h.onMove?.(d);
          break;
        case "office.avatar.left":
          h.onLeave?.(d.avatar_id);
          break;
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (closedRef.current) return;
      const delay = Math.min(1000 * 2 ** retryRef.current, 10000);
      retryRef.current += 1;
      setTimeout(connect, delay);
    };
    ws.onerror = () => ws.close();
  }, [sceneId]);

  useEffect(() => {
    closedRef.current = false;
    connect();
    return () => {
      closedRef.current = true;
      wsRef.current?.close();
    };
  }, [connect]);

  const move = useCallback(
    (x: number, y: number, facing = "down") => {
      const ws = wsRef.current;
      const m = meRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN || !m || !sceneId) return;
      ws.send(
        JSON.stringify({
          op: "presence.move",
          data: { scene_id: sceneId, avatar_id: m.avatar_id, x, y, facing, name: m.name, color: m.color, kind: m.kind },
        })
      );
    },
    [sceneId]
  );

  return { connected, move };
}

