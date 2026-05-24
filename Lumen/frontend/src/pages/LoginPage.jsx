/**
 * LoginPage — full-screen login / register form for Lumen FinOps OS.
 * Uses AuthContext for API calls. No router dependency.
 */

import { useState } from "react";
import { useAuth } from "../auth";

export default function LoginPage() {
  const { login, register, loading, error: authError } = useAuth();
  const [mode, setMode]         = useState("login");  // "login" | "register"
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [name, setName]         = useState("");
  const [localErr, setLocalErr] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setLocalErr("");
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        if (password.length < 8) {
          setLocalErr("Password must be at least 8 characters");
          return;
        }
        await register(email, password, name);
      }
    } catch (err) {
      setLocalErr(err.message);
    }
  }

  // Quick demo login
  async function demoLogin() {
    setLocalErr("");
    try {
      await login("admin@demo.local", "finops2024");
    } catch {
      // Demo account might not exist yet — try register first
      try {
        await register("admin@demo.local", "finops2024", "Demo Admin");
      } catch (err2) {
        setLocalErr(err2.message);
      }
    }
  }

  const err = localErr || authError;

  return (
    <div style={styles.shell}>
      {/* Left brand panel */}
      <div style={styles.brand}>
        <div style={styles.brandInner}>
          <div style={styles.logo}>
            <span style={styles.logoMark}>✦</span>
            <span style={styles.logoText}>Lumen</span>
          </div>
          <h1 style={styles.tagline}>FinOps OS</h1>
          <p style={styles.sub}>Cloud & AI Cost Intelligence</p>

          <div style={styles.pills}>
            {["Real-time AI spend", "FOCUS v1.0 normalisation", "Multi-cloud coverage", "Model router & swap"].map(f => (
              <div key={f} style={styles.pill}>
                <span style={styles.pillCheck}>✓</span> {f}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div style={styles.formPanel}>
        <div style={styles.card}>
          <div style={styles.tabs}>
            <button
              style={mode === "login" ? styles.tabActive : styles.tab}
              onClick={() => { setMode("login"); setLocalErr(""); }}
            >
              Sign in
            </button>
            <button
              style={mode === "register" ? styles.tabActive : styles.tab}
              onClick={() => { setMode("register"); setLocalErr(""); }}
            >
              Create account
            </button>
          </div>

          <form onSubmit={handleSubmit} style={styles.form}>
            {mode === "register" && (
              <label style={styles.label}>
                Full name
                <input
                  style={styles.input}
                  type="text"
                  placeholder="Jane Smith"
                  value={name}
                  onChange={e => setName(e.target.value)}
                />
              </label>
            )}

            <label style={styles.label}>
              Email address
              <input
                style={styles.input}
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoFocus
              />
            </label>

            <label style={styles.label}>
              Password
              <input
                style={styles.input}
                type="password"
                placeholder={mode === "register" ? "At least 8 characters" : "••••••••"}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </label>

            {err && <div style={styles.errBox}>{err}</div>}

            <button type="submit" style={styles.btn} disabled={loading}>
              {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          <div style={styles.divider}><span>or</span></div>

          <button style={styles.demoBtn} onClick={demoLogin} disabled={loading}>
            ⚡ Try demo account
          </button>

          <p style={styles.hint}>
            Demo credentials: <code>admin@demo.local</code> / <code>finops2024</code>
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Inline styles ──────────────────────────────────────────────────────────────
const C = {
  bg:      "#0d0d14",
  panel:   "#13131f",
  card:    "#1a1a2e",
  border:  "#2a2a42",
  accent:  "#7c6af7",
  accentH: "#9580ff",
  text:    "#e8e8f0",
  muted:   "#8888aa",
  err:     "#ff6b6b",
  success: "#4ade80",
};

const styles = {
  shell: {
    display: "flex", minHeight: "100vh", background: C.bg, fontFamily: "'Inter', system-ui, sans-serif",
  },
  brand: {
    flex: "0 0 420px", background: `linear-gradient(145deg, ${C.panel} 0%, #1a1040 100%)`,
    display: "flex", alignItems: "center", justifyContent: "center",
    borderRight: `1px solid ${C.border}`,
  },
  brandInner: { padding: "48px", maxWidth: "340px" },
  logo: { display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" },
  logoMark: { fontSize: "32px", color: C.accent },
  logoText: { fontSize: "28px", fontWeight: 700, color: C.text, letterSpacing: "-0.5px" },
  tagline: { fontSize: "36px", fontWeight: 800, color: C.text, margin: "0 0 8px", letterSpacing: "-1px" },
  sub: { color: C.muted, fontSize: "15px", margin: "0 0 36px" },
  pills: { display: "flex", flexDirection: "column", gap: "10px" },
  pill: { color: C.muted, fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" },
  pillCheck: { color: C.success, fontWeight: 700 },

  formPanel: {
    flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "40px",
  },
  card: {
    width: "100%", maxWidth: "420px", background: C.card,
    border: `1px solid ${C.border}`, borderRadius: "16px", padding: "40px",
  },
  tabs: { display: "flex", gap: "4px", marginBottom: "28px", background: C.panel, borderRadius: "8px", padding: "4px" },
  tab: {
    flex: 1, padding: "8px 12px", border: "none", borderRadius: "6px",
    background: "transparent", color: C.muted, cursor: "pointer", fontSize: "14px", fontWeight: 500,
  },
  tabActive: {
    flex: 1, padding: "8px 12px", border: "none", borderRadius: "6px",
    background: C.accent, color: "#fff", cursor: "pointer", fontSize: "14px", fontWeight: 600,
  },
  form: { display: "flex", flexDirection: "column", gap: "16px" },
  label: { display: "flex", flexDirection: "column", gap: "6px", fontSize: "13px", fontWeight: 600, color: C.muted },
  input: {
    padding: "10px 14px", background: C.panel, border: `1px solid ${C.border}`,
    borderRadius: "8px", color: C.text, fontSize: "15px", outline: "none",
    transition: "border-color 0.2s",
  },
  errBox: {
    background: "rgba(255,107,107,0.12)", border: `1px solid ${C.err}`,
    borderRadius: "8px", padding: "10px 14px", color: C.err, fontSize: "13px",
  },
  btn: {
    padding: "12px", background: C.accent, border: "none", borderRadius: "8px",
    color: "#fff", fontSize: "15px", fontWeight: 600, cursor: "pointer", marginTop: "4px",
    transition: "background 0.2s",
  },
  divider: {
    textAlign: "center", margin: "20px 0", color: C.muted, fontSize: "13px",
    position: "relative",
  },
  demoBtn: {
    width: "100%", padding: "11px", background: "transparent",
    border: `1px solid ${C.border}`, borderRadius: "8px",
    color: C.muted, fontSize: "14px", cursor: "pointer", transition: "border-color 0.2s",
  },
  hint: { marginTop: "16px", textAlign: "center", fontSize: "12px", color: C.muted },
};
