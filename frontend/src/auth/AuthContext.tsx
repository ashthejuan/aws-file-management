import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

const STORAGE_KEY = "fm.auth";

interface StoredAuth {
  token: string;
  expiresAt: number;
}

interface AuthContextValue {
  token: string | null;
  isAuthenticated: boolean;
  setSession: (token: string, expiresIn: number) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readStored(): StoredAuth | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredAuth;
    if (!parsed.token || typeof parsed.expiresAt !== "number") return null;
    if (parsed.expiresAt <= Date.now()) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [stored, setStored] = useState<StoredAuth | null>(() => readStored());

  useEffect(() => {
    if (!stored) return;
    const remaining = stored.expiresAt - Date.now();
    if (remaining <= 0) {
      setStored(null);
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    const timer = window.setTimeout(() => {
      setStored(null);
      localStorage.removeItem(STORAGE_KEY);
    }, remaining);
    return () => window.clearTimeout(timer);
  }, [stored]);

  const setSession = useCallback((token: string, expiresIn: number) => {
    const next: StoredAuth = {
      token,
      expiresAt: Date.now() + expiresIn * 1000,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setStored(next);
  }, []);

  const signOut = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setStored(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token: stored?.token ?? null,
      isAuthenticated: !!stored?.token,
      setSession,
      signOut,
    }),
    [stored, setSession, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
