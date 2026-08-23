"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, TOKEN_KEY, readToken } from "@/lib/api";
import type { AuthResponse, Organization, User } from "@/lib/types";

interface AuthContextValue {
  user: User | null;
  organization: Organization | null;
  loading: boolean;
  login: (organizationSlug: string, email: string, password: string) => Promise<void>;
  registerOrganization: (payload: Record<string, string>) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const applySession = useCallback((session: AuthResponse | null) => {
    setUser(session?.user || null);
    setOrganization(session?.organization || null);
  }, []);

  const refresh = useCallback(async () => {
    if (!readToken()) {
      applySession(null);
      setLoading(false);
      return;
    }
    try {
      applySession(await api.me());
    } catch {
      window.localStorage.removeItem(TOKEN_KEY);
      applySession(null);
    } finally {
      setLoading(false);
    }
  }, [applySession]);

  useEffect(() => {
    let active = true;
    async function restoreSession() {
      if (!readToken()) {
        if (active) {
          applySession(null);
          setLoading(false);
        }
        return;
      }
      try {
        const session = await api.me();
        if (active) applySession(session);
      } catch {
        window.localStorage.removeItem(TOKEN_KEY);
        if (active) applySession(null);
      } finally {
        if (active) setLoading(false);
      }
    }
    void restoreSession();
    return () => { active = false; };
  }, [applySession]);

  const login = useCallback(
    async (organizationSlug: string, email: string, password: string) => {
      const session = await api.login({
        organization_slug: organizationSlug,
        email,
        password,
      });
      window.localStorage.setItem(TOKEN_KEY, session.access_token);
      applySession(session);
      router.push("/dashboard");
    },
    [applySession, router],
  );

  const registerOrganization = useCallback(
    async (payload: Record<string, string>) => {
      const session = await api.register(payload);
      window.localStorage.setItem(TOKEN_KEY, session.access_token);
      applySession(session);
      router.push("/dashboard");
    },
    [applySession, router],
  );

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_KEY);
    applySession(null);
    if (pathname !== "/login") router.push("/login");
  }, [applySession, pathname, router]);

  const value = useMemo(
    () => ({ user, organization, loading, login, registerOrganization, logout, refresh }),
    [user, organization, loading, login, registerOrganization, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

export function AuthGuard({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, router, user]);

  if (loading || !user) {
    return (
      <div className="page-loader" role="status">
        <span className="spinner" />
        <span>Opening your workspace</span>
      </div>
    );
  }
  return children;
}
