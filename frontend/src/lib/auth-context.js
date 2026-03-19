"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined); // undefined = not yet checked
  const [loading, setLoading] = useState(true);
  const fetchedRef = useRef(false);

  const fetchUser = useCallback(async () => {
    try {
      const res = await apiFetch("/auth/me/");
      if (res.ok) {
        setUser(await res.json());
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Only fetch once on mount — not on every re-render
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    fetchUser();
  }, [fetchUser]);

  const login = useCallback(async (email, password) => {
    const res = await apiFetch("/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");
    setUser(data);
    return data;
  }, []);

  const signup = useCallback(async (email, password, displayName) => {
    const res = await apiFetch("/auth/signup/", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name: displayName }),
    });
    const data = await res.json();
    if (!res.ok) {
      const message =
        typeof data === "object"
          ? Object.values(data).flat().join(" ")
          : "Signup failed";
      throw new Error(message);
    }
    setUser(data);
    return data;
  }, []);

  const logout = useCallback(async () => {
    await apiFetch("/auth/logout/", { method: "POST" });
    setUser(null);
  }, []);

  // Stable context value — only changes when user or loading actually change
  const value = useMemo(
    () => ({ user: user ?? null, loading, login, signup, logout, refetchUser: fetchUser }),
    [user, loading, login, signup, logout, fetchUser]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
