"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Overview } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

const CARDS: { key: keyof Overview; label: string; icon: string; fmt?: (n: number) => string }[] = [
  { key: "projects", label: "Projetos", icon: "📁" },
  { key: "open_tasks", label: "Tarefas abertas", icon: "✅" },
  { key: "agents", label: "Agentes", icon: "🐹" },
  { key: "members", label: "Membros", icon: "👥" },
  { key: "documents", label: "Documentos", icon: "📄" },
  { key: "agent_runs", label: "Execuções de IA", icon: "⚡" },
  { key: "total_tokens", label: "Tokens consumidos", icon: "🔢" },
  {
    key: "total_cost_usd",
    label: "Custo estimado (USD)",
    icon: "💲",
    fmt: (n) => `$${n.toFixed(4)}`,
  },
];

export default function DashboardPage() {
  const { user, currentWorkspaceId } = useAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    api<Overview>("/admin/overview")
      .then(setData)
      .catch((e) => setError(e.message));
  }, [currentWorkspaceId]);

  return (
    <div>
      <PageHeader title={`Olá, ${user?.name?.split(" ")[0]} 👋`} subtitle="Visão geral do workspace" />
      <div className="p-6">
        {error && (
          <p className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {error} — esta visão requer papel de gestor ou administrador.
          </p>
        )}
        {!data && !error && <Spinner />}
        {data && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {CARDS.map((c) => (
              <Card key={c.key} className="p-4">
                <div className="text-2xl">{c.icon}</div>
                <div className="mt-2 text-2xl font-bold text-ink-900">
                  {c.fmt ? c.fmt(data[c.key]) : data[c.key]}
                </div>
                <div className="text-sm text-ink-700/60">{c.label}</div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
