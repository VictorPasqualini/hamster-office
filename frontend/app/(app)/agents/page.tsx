"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Agent } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  HamsterAvatar,
  Input,
  Label,
  Spinner,
  Textarea,
} from "@/components/ui";
import { useAuth } from "@/lib/auth";

const TYPES = ["commercial", "finance", "legal", "data_analyst", "developer", "support", "custom"];
const TOOLS = ["search_kb", "create_task", "update_task", "post_message", "generate_report"];

export default function AgentsPage() {
  const { currentWorkspaceId } = useAuth();
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "",
    type: "custom",
    persona: "",
    system_prompt: "",
    tools: [] as string[],
  });
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setAgents(await api<Agent[]>("/agents"));
  }

  useEffect(() => {
    setAgents(null);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspaceId]);

  function toggleTool(t: string) {
    setForm((f) => ({
      ...f,
      tools: f.tools.includes(t) ? f.tools.filter((x) => x !== t) : [...f.tools, t],
    }));
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api<Agent>("/agents", { method: "POST", body: form });
      setForm({ name: "", type: "custom", persona: "", system_prompt: "", tools: [] });
      setCreating(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    }
  }

  return (
    <div>
      <PageHeader
        title="Agentes"
        subtitle="Funcionários virtuais especializados (mesmo modelo, personas diferentes)"
        actions={<Button onClick={() => setCreating((v) => !v)}>+ Novo agente</Button>}
      />
      <div className="space-y-4 p-6">
        {creating && (
          <Card className="p-4">
            <form onSubmit={create} className="space-y-3">
              {error && (
                <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Nome</Label>
                  <Input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <Label>Tipo</Label>
                  <select
                    value={form.type}
                    onChange={(e) => setForm({ ...form, type: e.target.value })}
                    className="w-full rounded-lg border border-sand-200 bg-white px-3 py-2 text-sm"
                  >
                    {TYPES.map((t) => (
                      <option key={t}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <Label>Persona (descrição pública)</Label>
                <Input
                  value={form.persona}
                  onChange={(e) => setForm({ ...form, persona: e.target.value })}
                />
              </div>
              <div>
                <Label>Prompt do sistema (especialização)</Label>
                <Textarea
                  rows={3}
                  value={form.system_prompt}
                  onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>Ferramentas</Label>
                <div className="flex flex-wrap gap-2">
                  {TOOLS.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => toggleTool(t)}
                      className={`rounded-full px-3 py-1 text-xs font-medium ${
                        form.tools.includes(t)
                          ? "bg-accent-500 text-white"
                          : "bg-sand-100 text-ink-700"
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
              <Button type="submit">Criar agente</Button>
            </form>
          </Card>
        )}

        {!agents && <Spinner />}
        {agents && agents.length === 0 && <EmptyState title="Nenhum agente" />}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents?.map((a) => (
            <Card key={a.id} className="p-4">
              <div className="flex items-center gap-3">
                <HamsterAvatar kind="agent" color={(a.appearance?.color as string) || "orange"} size={40} />
                <div>
                  <div className="font-semibold text-ink-900">{a.name}</div>
                  <Badge tone="amber">{a.type}</Badge>
                </div>
              </div>
              {a.persona && <p className="mt-3 text-sm text-ink-700/70">{a.persona}</p>}
              <div className="mt-3 flex flex-wrap gap-1">
                {a.tools.map((t) => (
                  <span key={t} className="rounded bg-sand-100 px-1.5 py-0.5 text-xs text-ink-700">
                    {t}
                  </span>
                ))}
              </div>
              <div className="mt-3 text-xs text-ink-700/50">
                Modelo: {a.model} · temp {a.temperature}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
