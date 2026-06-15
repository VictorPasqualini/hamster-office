import type { ReactNode } from "react";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-sand-200 bg-white/60 px-6 py-4">
      <div>
        <h1 className="text-lg font-semibold text-ink-900">{title}</h1>
        {subtitle && <p className="text-sm text-ink-700/60">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
