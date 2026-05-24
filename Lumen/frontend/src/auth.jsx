/**
 * AuthContext — JWT token management for Lumen FinOps OS.
 *
 * Tokens are kept in memory (never localStorage) for XSS safety.
 * A background timer silently refreshes the access token before expiry.
 */

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8088";

// ── Context ────────────────────────────────────────────────────────────────────
const AuthCtx = createContext(null);

export function useAuth() {
  return useContext(AuthCtx);
}

// ── Provider ──────────────────────────────────────────────────────────────────
export function AuthProvider({ children }) {
  const [user, setUser]   = useState(null);   // { user_id, tenant_id, email, role }
  const [token, setToken] = useState(null);   // access token string
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  // Held in ref so the timer callback always gets the latest value
  const refreshTokenRef = useRef(null);
  const timerRef        = useRef(null);

  // ── Token refresh ────────────────────────────────────────────────────────────
  const scheduleRefresh = useCallback((ttlSeconds = 14 * 60) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    // Refresh 60 s before expiry
    const delay = Math.max((ttlSeconds - 60) * 1000, 5000);
    timerRef.current = setTimeout(async () => {
      if (!refreshTokenRef.current) return;
      try {
        const res = await fetch(`${API}/api/auth/refresh`, {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({ refresh_token: refreshTokenRef.current }),
        });
        if (res.ok) {
          const data = await res.json();
          setToken(data.access_token);
          refreshTokenRef.current = data.refresh_token;
          scheduleRefresh();
        } else {
          // Refresh failed — force logout
          _clear();
        }
      } catch {
        _clear();
      }
    }, delay);
  }, []);

  function _clear() {
    setUser(null);
    setToken(null);
    refreshTokenRef.current = null;
    if (timerRef.current) clearTimeout(timerRef.current);
  }

  function _applyTokens(data) {
    setToken(data.access_token);
    refreshTokenRef.current = data.refresh_token;
    setUser({
      user_id:   data.user_id,
      tenant_id: data.tenant_id,
      email:     data.email,
      role:      data.role,
    });
    scheduleRefresh(15 * 60);
  }

  // ── Login ────────────────────────────────────────────────────────────────────
  async function login(email, password) {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/auth/login`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Login failed");
      _applyTokens(data);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }

  // ── Register ─────────────────────────────────────────────────────────────────
  async function register(email, password, fullName = "") {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/auth/register`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email, password, full_name: fullName }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Registration failed");
      _applyTokens(data);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }

  // ── Logout ────────────────────────────────────────────────────────────────────
  async function logout() {
    if (refreshTokenRef.current && token) {
      try {
        await fetch(`${API}/api/auth/logout`, {
          method:  "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify({ refresh_token: refreshTokenRef.current }),
        });
      } catch { /* best-effort */ }
    }
    _clear();
  }

  // ── Authenticated fetch helper ────────────────────────────────────────────────
  function authFetch(url, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return fetch(url, { ...options, headers });
  }

  // Cleanup on unmount
  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  return (
    <AuthCtx.Provider value={{ user, token, loading, error, login, register, logout, authFetch, isAuthenticated: !!user }}>
      {children}
    </AuthCtx.Provider>
  );
}
