"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useRoomSocket } from "@/lib/ws";
import type { Agent, Member, Message, Room } from "@/lib/types";
import { Button, HamsterAvatar, Input, Spinner } from "./ui";

interface AuthorInfo {
  name: string;
  kind: "user" | "agent" | "system";
  color?: string;
}

export function ChatPanel({ projectId }: { projectId: string }) {
  const [roomId, setRoomId] = useState<string | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [authors, setAuthors] = useState<Record<string, AuthorInfo>>({});
  const [draft, setDraft] = useState("");
  const [resolving, setResolving] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { connected, messages, setMessages, send, agentBusy } = useRoomSocket(roomId);

  // Resolve (ou cria) a sala do projeto e carrega contexto.
  useEffect(() => {
    let active = true;
    (async () => {
      setResolving(true);
      const [rooms, projAgents, members, allAgents] = await Promise.all([
        api<Room[]>("/rooms"),
        api<{ id: string; name: string; type: string }[]>(`/projects/${projectId}/agents`),
        api<Member[]>("/workspaces/current/members").catch(() => [] as Member[]),
        api<Agent[]>("/agents").catch(() => [] as Agent[]),
      ]);
      if (!active) return;

      setAgents(allAgents);
      const map: Record<string, AuthorInfo> = {};
      for (const m of members) map[m.membership_id] = { name: m.name, kind: "user" };
      for (const a of allAgents)
        map[a.id] = { name: a.name, kind: "agent", color: (a.appearance?.color as string) || "orange" };
      setAuthors(map);

      let room = rooms.find((r) => r.project_id === projectId);
      if (!room) {
        room = await api<Room>("/rooms", {
          method: "POST",
          body: {
            type: "public_channel",
            name: "geral",
            project_id: projectId,
            agent_ids: projAgents.map((a) => a.id),
          },
        });
      }
      setRoomId(room.id);
      const history = await api<{ items: Message[] }>(`/rooms/${room.id}/messages`);
      setMessages(history.items);
      setResolving(false);
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, agentBusy]);

  const submit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const text = draft.trim();
      if (!text || !roomId) return;
      const ok = send(text);
      if (!ok) {
        // fallback HTTP se o socket não estiver aberto
        api(`/rooms/${roomId}/messages`, { method: "POST", body: { content: text } }).then(
          () => api<{ items: Message[] }>(`/rooms/${roomId}/messages`).then((r) => setMessages(r.items))
        );
      }
      setDraft("");
    },
    [draft, roomId, send, setMessages]
  );

  const agentChips = useMemo(() => agents.filter((a) => a.is_active), [agents]);

  if (resolving) return <Spinner />;

  return (
    <div className="flex h-[60vh] flex-col rounded-xl border border-sand-200 bg-white">
      <div className="flex items-center justify-between border-b border-sand-200 px-4 py-2">
        <span className="text-sm font-medium text-ink-800"># geral</span>
        <span className={`text-xs ${connected ? "text-emerald-600" : "text-ink-700/40"}`}>
          {connected ? "● online" : "○ conectando"}
        </span>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((m) => {
          const info = m.author_id ? authors[m.author_id] : undefined;
          const kind = m.author_kind;
          const name =
            kind === "system" ? "Sistema" : info?.name || (kind === "agent" ? "Agente" : "Usuário");
          return (
            <div key={m.id} className="flex gap-3">
              <HamsterAvatar kind={kind} color={info?.color} size={32} />
              <div className="min-w-0">
                <div className="flex items-baseline gap-2">
                  <span className="text-sm font-semibold text-ink-900">{name}</span>
                  {kind === "agent" && <span className="text-xs text-accent-600">IA</span>}
                </div>
                <p className="whitespace-pre-wrap break-words text-sm text-ink-800">{m.content}</p>
              </div>
            </div>
          );
        })}
        {agentBusy && (
          <div className="flex items-center gap-2 text-sm text-ink-700/50">
            <HamsterAvatar kind="agent" size={24} /> um agente está respondendo...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-sand-200 p-3">
        {agentChips.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1">
            {agentChips.map((a) => (
              <button
                key={a.id}
                onClick={() => setDraft((d) => `${d}@${a.name} `)}
                className="rounded-full bg-sand-100 px-2 py-0.5 text-xs text-ink-700 hover:bg-sand-200"
              >
                @{a.name}
              </button>
            ))}
          </div>
        )}
        <form onSubmit={submit} className="flex gap-2">
          <Input
            placeholder="Mensagem... mencione @Agente para acionar a IA"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <Button type="submit">Enviar</Button>
        </form>
      </div>
    </div>
  );
}
