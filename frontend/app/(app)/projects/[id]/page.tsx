"use client";

import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Spinner } from "@/components/ui";
import { TaskBoard } from "@/components/TaskBoard";
import { ChatPanel } from "@/components/ChatPanel";
import { DocsPanel } from "@/components/DocsPanel";

type Tab = "tasks" | "chat" | "docs";

const TABS: { key: Tab; label: string }[] = [
  { key: "tasks", label: "📋 Tarefas" },
  { key: "chat", label: "💬 Chat" },
  { key: "docs", label: "📄 Documentos" },
];

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [project, setProject] = useState<Project | null>(null);
  const [tab, setTab] = useState<Tab>("tasks");

  useEffect(() => {
    api<Project>(`/projects/${id}`).then(setProject);
  }, [id]);

  if (!project) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={project.name}
        subtitle={project.client_name ? `Cliente: ${project.client_name}` : project.description || ""}
      />
      <div className="border-b border-sand-200 bg-white/60 px-6">
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`border-b-2 px-4 py-3 text-sm font-medium transition ${
                tab === t.key
                  ? "border-accent-500 text-accent-600"
                  : "border-transparent text-ink-700/60 hover:text-ink-800"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {tab === "tasks" && <TaskBoard projectId={id} />}
        {tab === "chat" && <ChatPanel projectId={id} />}
        {tab === "docs" && <DocsPanel projectId={id} />}
      </div>
    </div>
  );
}
