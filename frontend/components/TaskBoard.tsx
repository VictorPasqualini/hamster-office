"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Task, TaskStatus } from "@/lib/types";
import { Badge, Button, Input, Spinner } from "./ui";

const COLS: { key: TaskStatus; label: string }[] = [
  { key: "todo", label: "A fazer" },
  { key: "in_progress", label: "Em andamento" },
  { key: "review", label: "Revisão" },
  { key: "done", label: "Concluído" },
];

const PRIORITY_TONE: Record<string, "gray" | "blue" | "amber" | "red"> = {
  low: "gray",
  medium: "blue",
  high: "amber",
  urgent: "red",
};

const NEXT: Partial<Record<TaskStatus, TaskStatus>> = {
  todo: "in_progress",
  in_progress: "review",
  review: "done",
};

export function TaskBoard({ projectId }: { projectId: string }) {
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("medium");

  async function load() {
    setTasks(await api<Task[]>(`/projects/${projectId}/tasks`));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await api<Task>(`/projects/${projectId}/tasks`, {
      method: "POST",
      body: { title, priority },
    });
    setTitle("");
    await load();
  }

  async function move(task: Task, status: TaskStatus) {
    await api(`/tasks/${task.id}/status`, { method: "POST", body: { status } });
    await load();
  }

  if (!tasks) return <Spinner />;

  return (
    <div className="space-y-4">
      <form onSubmit={create} className="flex gap-2">
        <Input
          placeholder="Nova tarefa..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
          className="rounded-lg border border-sand-200 bg-white px-2 text-sm"
        >
          <option value="low">Baixa</option>
          <option value="medium">Média</option>
          <option value="high">Alta</option>
          <option value="urgent">Urgente</option>
        </select>
        <Button type="submit">Adicionar</Button>
      </form>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {COLS.map((col) => {
          const items = tasks.filter((t) => t.status === col.key);
          return (
            <div key={col.key} className="rounded-xl bg-sand-100/60 p-3">
              <div className="mb-2 flex items-center justify-between px-1">
                <span className="text-sm font-semibold text-ink-800">{col.label}</span>
                <span className="text-xs text-ink-700/50">{items.length}</span>
              </div>
              <div className="space-y-2">
                {items.map((t) => (
                  <div
                    key={t.id}
                    className="rounded-lg border border-sand-200 bg-white p-3 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm text-ink-800">{t.title}</p>
                      <Badge tone={PRIORITY_TONE[t.priority]}>{t.priority}</Badge>
                    </div>
                    {t.assignee_kind === "agent" && (
                      <p className="mt-1 text-xs text-accent-600">🐹 agente</p>
                    )}
                    {NEXT[t.status] && (
                      <button
                        onClick={() => move(t, NEXT[t.status]!)}
                        className="mt-2 text-xs font-medium text-accent-600 hover:underline"
                      >
                        Mover para {COLS.find((c) => c.key === NEXT[t.status])?.label} →
                      </button>
                    )}
                  </div>
                ))}
                {items.length === 0 && (
                  <p className="px-1 py-4 text-center text-xs text-ink-700/40">vazio</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
