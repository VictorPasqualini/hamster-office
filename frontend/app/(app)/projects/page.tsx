"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Badge, Button, Card, EmptyState, Input, Label, Spinner, Textarea } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function ProjectsPage() {
  const { currentWorkspaceId } = useAuth();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", client_name: "", description: "" });
  const [saving, setSaving] = useState(false);

  async function load() {
    setProjects(await api<Project[]>("/projects"));
  }

  useEffect(() => {
    setProjects(null);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspaceId]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api<Project>("/projects", { method: "POST", body: form });
      setForm({ name: "", client_name: "", description: "" });
      setCreating(false);
      await load();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Projetos"
        subtitle="Espaços de trabalho com tarefas, conversas e documentos"
        actions={<Button onClick={() => setCreating((v) => !v)}>+ Novo projeto</Button>}
      />
      <div className="space-y-4 p-6">
        {creating && (
          <Card className="p-4">
            <form onSubmit={create} className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div>
                <Label>Nome</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>Cliente</Label>
                <Input
                  value={form.client_name}
                  onChange={(e) => setForm({ ...form, client_name: e.target.value })}
                />
              </div>
              <div className="md:col-span-2">
                <Label>Descrição</Label>
                <Textarea
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
              <div className="md:col-span-2">
                <Button type="submit" disabled={saving}>
                  {saving ? "Salvando..." : "Criar"}
                </Button>
              </div>
            </form>
          </Card>
        )}

        {!projects && <Spinner />}
        {projects && projects.length === 0 && (
          <EmptyState title="Nenhum projeto ainda" hint="Crie o primeiro para começar." />
        )}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects?.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`}>
              <Card className="h-full p-4 transition hover:border-accent-400">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-ink-900">{p.name}</h3>
                  <Badge tone={p.status === "active" ? "green" : "gray"}>{p.status}</Badge>
                </div>
                {p.client_name && (
                  <p className="mt-1 text-sm text-ink-700/60">Cliente: {p.client_name}</p>
                )}
                {p.description && (
                  <p className="mt-2 line-clamp-2 text-sm text-ink-700/70">{p.description}</p>
                )}
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
