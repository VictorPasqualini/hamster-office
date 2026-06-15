"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: "🏠" },
  { href: "/office", label: "Escritório", icon: "🏢" },
  { href: "/projects", label: "Projetos", icon: "📁" },
  { href: "/agents", label: "Agentes", icon: "🐹" },
  { href: "/admin", label: "Administração", icon: "⚙️" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, workspaces, currentWorkspaceId, switchWorkspace, logout } = useAuth();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-sand-200 bg-white">
      <div className="flex items-center gap-2 px-4 py-4">
        <span className="text-2xl">🐹</span>
        <span className="font-bold text-ink-900">Hamster Office</span>
      </div>

      {/* Workspace switcher */}
      <div className="px-3">
        <select
          value={currentWorkspaceId || ""}
          onChange={(e) => switchWorkspace(e.target.value)}
          className="w-full rounded-lg border border-sand-200 bg-sand-50 px-2 py-2 text-sm"
        >
          {workspaces.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name} · {w.role}
            </option>
          ))}
        </select>
      </div>

      <nav className="mt-4 flex-1 space-y-1 px-3">
        {NAV.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                active ? "bg-accent-500 text-white" : "text-ink-700 hover:bg-sand-100"
              }`}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sand-200 p-3">
        <div className="mb-2 truncate px-1 text-sm text-ink-700">{user?.name}</div>
        <button
          onClick={logout}
          className="w-full rounded-lg px-3 py-2 text-left text-sm text-ink-700/70 hover:bg-sand-100"
        >
          Sair
        </button>
      </div>
    </aside>
  );
}
