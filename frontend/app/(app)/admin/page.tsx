"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AuditEvent, Member, UsageRow } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Badge, Card, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

type Section = "members" | "usage" | "audit";

export default function AdminPage() {
  const { currentWorkspaceId } = useAuth();
  const [section, setSection] = useState<Section>("usage");
  const [members, setMembers] = useState<Member[] | null>(null);
  const [usage, setUsage] = useState<UsageRow[] | null>(null);
  const [audit, setAudit] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    setMembers(null);
    setUsage(null);
    setAudit(null);
    api<Member[]>("/workspaces/current/members").then(setMembers).catch(() => setMembers([]));
    api<UsageRow[]>("/admin/usage").then(setUsage).catch((e) => setError(e.message));
    api<AuditEvent[]>("/admin/audit").then(setAudit).catch(() => setAudit([]));
  }, [currentWorkspaceId]);

  return (
    <div>
      <PageHeader title="Administração" subtitle="Membros, consumo de IA e auditoria" />
      <div className="border-b border-sand-200 bg-white/60 px-6">
        <div className="flex gap-1">
          {(["usage", "members", "audit"] as Section[]).map((s) => (
            <button
              key={s}
              onClick={() => setSection(s)}
              className={`border-b-2 px-4 py-3 text-sm font-medium capitalize transition ${
                section === s
                  ? "border-accent-500 text-accent-600"
                  : "border-transparent text-ink-700/60 hover:text-ink-800"
              }`}
            >
              {s === "usage" ? "Consumo & Custos" : s === "members" ? "Membros" : "Auditoria"}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {error && (
          <p className="mb-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {error} — requer papel de gestor ou administrador.
          </p>
        )}

        {section === "usage" && (
          <Card className="overflow-hidden">
            {!usage ? (
              <div className="p-6">
                <Spinner />
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-sand-100 text-left text-ink-700">
                  <tr>
                    <th className="px-4 py-2">Agente</th>
                    <th className="px-4 py-2">Tipo</th>
                    <th className="px-4 py-2 text-right">Execuções</th>
                    <th className="px-4 py-2 text-right">Tokens</th>
                    <th className="px-4 py-2 text-right">Custo (USD)</th>
                  </tr>
                </thead>
                <tbody>
                  {usage.map((u) => (
                    <tr key={u.agent_id} className="border-t border-sand-200">
                      <td className="px-4 py-2 font-medium text-ink-900">🐹 {u.name}</td>
                      <td className="px-4 py-2">
                        <Badge tone="amber">{u.type}</Badge>
                      </td>
                      <td className="px-4 py-2 text-right">{u.run_count}</td>
                      <td className="px-4 py-2 text-right">{u.total_tokens}</td>
                      <td className="px-4 py-2 text-right">${u.total_cost_usd.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        )}

        {section === "members" && (
          <Card className="overflow-hidden">
            {!members ? (
              <div className="p-6">
                <Spinner />
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-sand-100 text-left text-ink-700">
                  <tr>
                    <th className="px-4 py-2">Nome</th>
                    <th className="px-4 py-2">Email</th>
                    <th className="px-4 py-2">Papel</th>
                    <th className="px-4 py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((m) => (
                    <tr key={m.membership_id} className="border-t border-sand-200">
                      <td className="px-4 py-2 font-medium text-ink-900">{m.name}</td>
                      <td className="px-4 py-2 text-ink-700/70">{m.email}</td>
                      <td className="px-4 py-2">
                        <Badge tone="blue">{m.role}</Badge>
                      </td>
                      <td className="px-4 py-2">
                        <Badge tone={m.status === "active" ? "green" : "gray"}>{m.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        )}

        {section === "audit" && (
          <Card className="divide-y divide-sand-200">
            {!audit ? (
              <div className="p-6">
                <Spinner />
              </div>
            ) : audit.length === 0 ? (
              <div className="p-6 text-sm text-ink-700/50">Sem eventos.</div>
            ) : (
              audit.map((e) => (
                <div key={e.id} className="flex items-center justify-between px-4 py-2 text-sm">
                  <div>
                    <span className="font-medium text-ink-900">{e.type}</span>
                    <span className="ml-2 text-ink-700/50">{e.actor_kind}</span>
                  </div>
                  <span className="text-xs text-ink-700/40">
                    {e.occurred_at ? new Date(e.occurred_at).toLocaleString("pt-BR") : ""}
                  </span>
                </div>
              ))
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
