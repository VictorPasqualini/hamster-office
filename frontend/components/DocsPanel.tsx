"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { DocumentItem } from "@/lib/types";
import { Badge, Button, EmptyState, Input, Spinner } from "./ui";

const STATUS_TONE: Record<string, "gray" | "amber" | "green" | "red"> = {
  uploaded: "gray",
  processing: "amber",
  indexed: "green",
  failed: "red",
};

interface UploadUrl {
  document_id: string;
  object_key: string;
  upload_url: string;
}

export function DocsPanel({ projectId }: { projectId: string }) {
  const [docs, setDocs] = useState<DocumentItem[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ content: string; score: number }[] | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    const all = await api<DocumentItem[]>("/documents");
    setDocs(all.filter((d) => d.project_id === projectId || !d.project_id));
  }

  useEffect(() => {
    setDocs(null);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function upload(file: File) {
    setUploading(true);
    try {
      const { document_id, upload_url } = await api<UploadUrl>("/documents/upload-url", {
        method: "POST",
        body: { filename: file.name, mime: file.type, project_id: projectId, title: file.name },
      });
      const put = await fetch(upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type || "application/octet-stream" },
      });
      if (!put.ok) throw new Error("Falha no upload ao storage");
      await api(`/documents/${document_id}/process`, { method: "POST" });
      await load();
      // Atualiza status após indexação (assíncrona)
      setTimeout(load, 2500);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro no upload");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function search(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    const r = await api<{ chunks: { content: string; score: number }[] }>("/knowledge/search", {
      method: "POST",
      body: { query, project_id: projectId, top_k: 5 },
    });
    setResults(r.chunks);
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
          />
          <Button onClick={() => fileRef.current?.click()} disabled={uploading}>
            {uploading ? "Enviando..." : "📎 Enviar documento"}
          </Button>
          <span className="text-xs text-ink-700/50">
            PDF, TXT, Markdown — será indexado para RAG
          </span>
        </div>

        <div className="mt-4 space-y-2">
          {!docs && <Spinner />}
          {docs && docs.length === 0 && (
            <EmptyState title="Sem documentos" hint="Envie arquivos para a base de conhecimento." />
          )}
          {docs?.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between rounded-lg border border-sand-200 bg-white px-4 py-2"
            >
              <span className="truncate text-sm text-ink-800">📄 {d.title}</span>
              <Badge tone={STATUS_TONE[d.status] || "gray"}>{d.status}</Badge>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-sand-200 bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold text-ink-800">Testar busca semântica (RAG)</h3>
        <form onSubmit={search} className="flex gap-2">
          <Input
            placeholder="Ex.: qual o prazo de entrega?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <Button type="submit">Buscar</Button>
        </form>
        {results && (
          <div className="mt-3 space-y-2">
            {results.length === 0 && (
              <p className="text-sm text-ink-700/50">Nenhum trecho encontrado.</p>
            )}
            {results.map((r, i) => (
              <div key={i} className="rounded-lg bg-sand-50 p-3 text-sm text-ink-700">
                <span className="float-right text-xs text-accent-600">
                  {(r.score * 100).toFixed(0)}%
                </span>
                {r.content.slice(0, 300)}
                {r.content.length > 300 ? "…" : ""}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
