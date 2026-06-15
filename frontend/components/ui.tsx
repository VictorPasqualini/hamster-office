"use client";

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

function cx(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

export function Button({
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "outline" | "danger";
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:opacity-50 disabled:pointer-events-none";
  const variants = {
    primary: "bg-accent-500 text-white hover:bg-accent-600 shadow-sm",
    ghost: "text-ink-700 hover:bg-sand-100",
    outline: "border border-sand-200 bg-white hover:bg-sand-50 text-ink-800",
    danger: "bg-red-600 text-white hover:bg-red-700",
  };
  return <button className={cx(base, variants[variant], className)} {...props} />;
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cx(
        "w-full rounded-lg border border-sand-200 bg-white px-3 py-2 text-sm outline-none placeholder:text-ink-700/40 focus:border-accent-400 focus:ring-2 focus:ring-accent-400/20",
        className
      )}
      {...props}
    />
  );
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cx(
        "w-full rounded-lg border border-sand-200 bg-white px-3 py-2 text-sm outline-none focus:border-accent-400 focus:ring-2 focus:ring-accent-400/20",
        className
      )}
      {...props}
    />
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("rounded-xl border border-sand-200 bg-white shadow-soft", className)}>
      {children}
    </div>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <label className="mb-1 block text-xs font-medium text-ink-700">{children}</label>;
}

const TONE: Record<string, string> = {
  default: "bg-sand-100 text-ink-700",
  green: "bg-emerald-100 text-emerald-800",
  amber: "bg-amber-100 text-amber-800",
  blue: "bg-blue-100 text-blue-800",
  red: "bg-red-100 text-red-800",
  gray: "bg-slate-100 text-slate-700",
};

export function Badge({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: keyof typeof TONE;
}) {
  return (
    <span className={cx("rounded-full px-2 py-0.5 text-xs font-medium", TONE[tone])}>
      {children}
    </span>
  );
}

const HAMSTER_COLORS: Record<string, string> = {
  orange: "bg-accent-400",
  green: "bg-emerald-400",
  blue: "bg-blue-400",
  pink: "bg-pink-400",
  gray: "bg-slate-400",
};

/** Avatar simples de hamster (emoji + cor). Placeholder do avatar isométrico futuro. */
export function HamsterAvatar({
  color = "orange",
  size = 32,
  kind = "agent",
}: {
  color?: string;
  size?: number;
  kind?: "agent" | "user" | "system";
}) {
  const bg = kind === "user" ? "bg-ink-700" : HAMSTER_COLORS[color] || HAMSTER_COLORS.orange;
  const emoji = kind === "system" ? "📣" : kind === "user" ? "🧑" : "🐹";
  return (
    <div
      className={cx("flex shrink-0 items-center justify-center rounded-full text-white", bg)}
      style={{ width: size, height: size, fontSize: size * 0.5 }}
    >
      {emoji}
    </div>
  );
}

export function Spinner() {
  return (
    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-accent-400 border-t-transparent" />
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-sand-200 py-12 text-center">
      <div className="text-3xl">🐹</div>
      <p className="mt-2 font-medium text-ink-800">{title}</p>
      {hint && <p className="mt-1 text-sm text-ink-700/60">{hint}</p>}
    </div>
  );
}
