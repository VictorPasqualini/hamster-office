"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { OfficeAvatar, Scene } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Spinner } from "@/components/ui";
import { OfficeCanvas } from "@/components/OfficeCanvas";
import { useAuth } from "@/lib/auth";

export default function OfficePage() {
  const { currentWorkspaceId } = useAuth();
  const [scene, setScene] = useState<Scene | null>(null);
  const [myAvatar, setMyAvatar] = useState<OfficeAvatar | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setScene(null);
    setError(null);
    Promise.all([api<Scene>("/office/scene"), api<OfficeAvatar>("/office/avatars/me")])
      .then(([s, a]) => {
        setScene(s);
        setMyAvatar(a);
      })
      .catch((e) => setError(e.message));
  }, [currentWorkspaceId]);

  return (
    <div>
      <PageHeader
        title="Escritório"
        subtitle="Ambiente isométrico — os hamsters (agentes) e colegas andam pela sala em tempo real"
      />
      <div className="p-6">
        {error && (
          <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
        )}
        {!scene && !error && <Spinner />}
        {scene && <OfficeCanvas scene={scene} myAvatar={myAvatar} />}
        {scene && (
          <p className="mt-4 text-sm text-ink-700/60">
            🐹 = agentes · 🧑 = pessoas. Abra em duas abas para ver a movimentação sincronizada.
            Decoração e móveis vêm da base de dados (catálogo + posicionamento).
          </p>
        )}
      </div>
    </div>
  );
}
