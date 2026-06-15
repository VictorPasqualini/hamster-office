"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, session } from "./api";
import type { LoginResponse, User, WorkspaceBrief } from "./types";

interface AuthState {
  ready: boolean;
  user: User | null;
  workspaces: WorkspaceBrief[];
  currentWorkspaceId: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  switchWorkspace: (id: string) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceBrief[]>([]);
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState<string | null>(null);

  const hydrate = useCallback(async () => {
    if (!session.token) {
      setReady(true);
      return;
    }
    try {
      const me = await api<{ user: User; workspaces: WorkspaceBrief[] }>("/auth/me", {
        tenant: false,
      });
      setUser(me.user);
      setWorkspaces(me.workspaces);
      const stored = session.workspaceId;
      const valid = me.workspaces.find((w) => w.id === stored);
      const wid = valid?.id || me.workspaces[0]?.id || null;
      if (wid) {
        session.setWorkspace(wid);
        setCurrentWorkspaceId(wid);
      }
    } catch {
      session.clear();
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const applyLogin = useCallback((data: LoginResponse) => {
    session.set(data.access_token, data.refresh_token);
    setWorkspaces(data.workspaces);
    const wid = data.workspaces[0]?.id || null;
    if (wid) {
      session.setWorkspace(wid);
      setCurrentWorkspaceId(wid);
    }
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await api<LoginResponse>("/auth/login", {
        method: "POST",
        body: { email, password },
        auth: false,
        tenant: false,
      });
      applyLogin(data);
      await hydrate();
    },
    [applyLogin, hydrate]
  );

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      const data = await api<LoginResponse>("/auth/register", {
        method: "POST",
        body: { name, email, password },
        auth: false,
        tenant: false,
      });
      applyLogin(data);
      await hydrate();
    },
    [applyLogin, hydrate]
  );

  const logout = useCallback(() => {
    session.clear();
    setUser(null);
    setWorkspaces([]);
    setCurrentWorkspaceId(null);
  }, []);

  const switchWorkspace = useCallback((id: string) => {
    session.setWorkspace(id);
    setCurrentWorkspaceId(id);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ready,
        user,
        workspaces,
        currentWorkspaceId,
        login,
        register,
        logout,
        switchWorkspace,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return ctx;
}
