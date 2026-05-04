"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import {
  clearAuthSession,
  getStoredUser,
  storeAuthSession,
  storeUser,
} from "@/lib/auth";
import type { LoginResponse, RegisterInput, User } from "@/lib/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedUser = getStoredUser();
    setUser(storedUser);

    if (!storedUser) {
      setIsLoading(false);
      return;
    }

    api
      .me()
      .then((freshUser) => {
        storeUser(freshUser);
        setUser(freshUser);
      })
      .catch(() => {
        clearAuthSession();
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      async login(username: string, password: string) {
        const session: LoginResponse = await api.login(username, password);
        storeAuthSession(session);
        setUser(session.user);
      },
      async register(input: RegisterInput) {
        return api.register(input);
      },
      async logout() {
        await api.logout();
        setUser(null);
      },
      async refreshUser() {
        const freshUser = await api.me();
        storeUser(freshUser);
        setUser(freshUser);
      },
    }),
    [user, isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}

