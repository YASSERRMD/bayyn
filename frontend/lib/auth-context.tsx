"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, clearStoredToken, getStoredToken, setStoredToken, UserResponse } from "./api";

interface AuthContextValue {
  user: UserResponse | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setIsLoading(false);
      return;
    }
    api.getMe()
      .then(setUser)
      .catch(() => clearStoredToken())
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await api.login(email, password);
    setStoredToken(access_token);
    const me = await api.getMe();
    setUser(me);
  }, []);

  const register = useCallback(async (email: string, password: string, name?: string) => {
    const { access_token } = await api.register(email, password, name);
    setStoredToken(access_token);
    const me = await api.getMe();
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    clearStoredToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
