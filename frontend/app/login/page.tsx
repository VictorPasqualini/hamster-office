"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Button, Card, Input, Label } from "@/components/ui";

export default function LoginPage() {
  const { login, register } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("ana@acme.com");
  const [password, setPassword] = useState("hamster123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(name, email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao autenticar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="text-5xl">🐹</div>
          <h1 className="mt-2 text-2xl font-bold text-ink-900">Hamster Office</h1>
          <p className="text-sm text-ink-700/60">
            Seu escritório de agentes de IA
          </p>
        </div>

        <Card className="p-6">
          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <div>
                <Label>Nome</Label>
                <Input value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
            )}
            <div>
              <Label>Email</Label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <Label>Senha</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Entrando..." : mode === "login" ? "Entrar" : "Criar conta"}
            </Button>
          </form>

          <button
            className="mt-4 w-full text-center text-sm text-ink-700/60 hover:text-accent-600"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
          >
            {mode === "login"
              ? "Não tem conta? Cadastre-se"
              : "Já tem conta? Entrar"}
          </button>
        </Card>

        <p className="mt-4 text-center text-xs text-ink-700/50">
          Demo: ana@acme.com / hamster123
        </p>
      </div>
    </div>
  );
}
