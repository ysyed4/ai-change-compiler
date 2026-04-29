"use client";

import { useEffect, useState } from "react";

type Policy = {
  id: string;
  name: string;
  description: string;
  condition_expr: string;
  enforcement: string;
  enabled: boolean;
  scope_platform: string;
  scope_change_type: string;
  created_at: string;
  updated_at: string;
};

export default function PoliciesPage() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
  const [token, setToken] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    return window.localStorage.getItem("cc_token") || "";
  });
  const withAuthHeaders = (base: Record<string, string> = {}): Record<string, string> => {
    if (!token) return base;
    return { ...base, Authorization: `Bearer ${token}` };
  };

  const [policies, setPolicies] = useState<Policy[]>([]);
  const [error, setError] = useState<string>("");

  const [name, setName] = useState("block-high-risk");
  const [description, setDescription] = useState("Block changes when risk_score exceeds 90");
  const [conditionExpr, setConditionExpr] = useState("risk_score > 90");
  const [enforcement, setEnforcement] = useState("hard_stop");

  const refresh = async () => {
    setError("");
    const resp = await fetch(`${apiBase}/policies`, { headers: withAuthHeaders() });
    const data = await resp.json();
    if (!resp.ok) {
      setError(data.detail || "Failed to load policies");
      return;
    }
    setPolicies(data);
  };

  const create = async () => {
    setError("");
    const resp = await fetch(`${apiBase}/policies`, {
      method: "POST",
      headers: withAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        name,
        description,
        condition_expr: conditionExpr,
        enforcement,
        enabled: true,
        scope_platform: "kafka",
        scope_change_type: "restart_component",
      }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      setError(data.detail || "Failed to create policy");
      return;
    }
    await refresh();
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <main>
      <h2>Policies</h2>
      <p>Admin-only create/update. This page is intentionally minimal for pilots.</p>

      <section style={{ border: "1px solid #ddd", padding: "1rem", marginBottom: "1rem" }}>
        <h3>Auth token</h3>
        <label>
          Token:
          <input
            value={token}
            onChange={(e) => {
              const v = e.target.value;
              setToken(v);
              if (typeof window !== "undefined") window.localStorage.setItem("cc_token", v);
            }}
            style={{ marginLeft: "0.5rem", width: "min(900px, 90vw)" }}
          />
        </label>
      </section>

      <section style={{ border: "1px solid #ddd", padding: "1rem" }}>
        <h3>Create policy (admin)</h3>
        <div style={{ display: "grid", gap: "0.5rem", maxWidth: "900px" }}>
          <label>
            Name:
            <input value={name} onChange={(e) => setName(e.target.value)} style={{ marginLeft: "0.5rem" }} />
          </label>
          <label>
            Description:
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{ marginLeft: "0.5rem", width: "100%" }}
            />
          </label>
          <label>
            Condition:
            <input
              value={conditionExpr}
              onChange={(e) => setConditionExpr(e.target.value)}
              style={{ marginLeft: "0.5rem", width: "100%" }}
            />
          </label>
          <label>
            Enforcement:
            <select value={enforcement} onChange={(e) => setEnforcement(e.target.value)} style={{ marginLeft: "0.5rem" }}>
              <option value="hard_stop">hard_stop</option>
              <option value="manual_approval">manual_approval</option>
            </select>
          </label>
          <button onClick={create}>Create</button>
        </div>
      </section>

      {error && <p style={{ marginTop: "0.75rem", color: "#b00020" }}>{error}</p>}

      <section style={{ marginTop: "1rem" }}>
        <h3>Existing policies</h3>
        <button onClick={refresh}>Refresh</button>
        <ul style={{ marginTop: "0.75rem" }}>
          {policies.map((p) => (
            <li key={p.id}>
              <strong>{p.name}</strong> ({p.enforcement}) — {p.enabled ? "enabled" : "disabled"} — <code>{p.condition_expr}</code>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

