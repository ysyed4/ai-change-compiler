"use client";

import { useState } from "react";

import { DecisionPanel } from "@/components/decision-panel";

type ChangeSubmission = {
  platform: string;
  change_type: string;
  target: {
    type: string;
    id: string;
  };
  reason: string;
};

type Evaluation = {
  change_id: string;
  decision: string;
  risk_score: number;
  explanation: string[];
  constraints: string[];
  telemetry_source_status: string;
  metadata_source_status: string;
};

type ExecuteResult = {
  change_id: string;
  status: string;
  execution_mode: string;
};

type AuditEvent = {
  event_type: string;
  stage: string;
  created_at: string;
  payload: Record<string, unknown>;
};

const initialSubmission: ChangeSubmission = {
  platform: "kafka",
  change_type: "restart_component",
  target: { type: "broker", id: "broker-1" },
  reason: "scheduled maintenance",
};

export default function ChangesPage() {
  const [submission, setSubmission] = useState<ChangeSubmission>(initialSubmission);
  const [changeId, setChangeId] = useState<string>("");
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [execution, setExecution] = useState<ExecuteResult | null>(null);
  const [timeline, setTimeline] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string>("");
  const [token, setToken] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    return window.localStorage.getItem("cc_token") || "";
  });

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
  const authBase = (process.env.NEXT_PUBLIC_AUTH_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

  const authHeaders: HeadersInit = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  const saveToken = (value: string) => {
    setToken(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("cc_token", value);
    }
  };

  const devLogin = async (roles: string[]) => {
    setError("");
    const resp = await fetch(`${authBase}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "demo@company.com", roles }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      setError(data.detail || "Failed to login");
      return;
    }
    saveToken(data.access_token);
  };

  const submitChange = async () => {
    setError("");
    const response = await fetch(`${apiBase}/changes`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify(submission),
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail || "Failed to submit change");
      return;
    }
    setChangeId(data.change_id);
    setEvaluation(null);
    setExecution(null);
    setTimeline([]);
  };

  const evaluateChange = async () => {
    if (!changeId) return;

    setError("");
    const response = await fetch(`${apiBase}/changes/${changeId}/evaluate`, {
      method: "POST",
      headers: { ...authHeaders },
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail || "Failed to evaluate change");
      return;
    }
    setEvaluation(data);
  };

  const executeChange = async () => {
    if (!changeId) return;

    setError("");
    const response = await fetch(`${apiBase}/changes/${changeId}/execute`, {
      method: "POST",
      headers: { ...authHeaders },
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.detail || "Failed to execute change");
    } else {
      setExecution(data);
    }

    const auditResponse = await fetch(`${apiBase}/changes/${changeId}/audit`, {
      headers: { ...authHeaders },
    });
    const auditData = await auditResponse.json();
    setTimeline(auditData);
  };

  return (
    <main>
      <h2>Kafka Broker Restart Workflow</h2>
      <p>Submit, evaluate, and execute a guarded broker restart.</p>

      <section style={{ border: "1px solid #ddd", padding: "1rem", marginBottom: "1rem" }}>
        <h3>Auth</h3>
        <p style={{ marginTop: 0 }}>
          This UI sends a Bearer token. Use dev login buttons for local demo, or paste a JWT.
        </p>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button onClick={() => devLogin(["requester", "viewer"])}>Dev login: requester</button>
          <button onClick={() => devLogin(["approver", "viewer"])}>Dev login: approver</button>
          <button onClick={() => devLogin(["executor", "viewer"])}>Dev login: executor</button>
          <button onClick={() => devLogin(["admin"])}>Dev login: admin</button>
          <button
            onClick={() => {
              saveToken("");
            }}
          >
            Clear token
          </button>
        </div>
        <label style={{ display: "block", marginTop: "0.75rem" }}>
          Token:
          <input
            value={token}
            onChange={(e) => saveToken(e.target.value)}
            placeholder="paste JWT here"
            style={{ marginLeft: "0.5rem", width: "min(900px, 90vw)" }}
          />
        </label>
      </section>

      <label>
        Broker ID:
        <input
          value={submission.target.id}
          onChange={(e) =>
            setSubmission((prev) => ({ ...prev, target: { ...prev.target, id: e.target.value } }))
          }
          style={{ marginLeft: "0.5rem" }}
        />
      </label>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
        <button onClick={submitChange}>1) Submit</button>
        <button onClick={evaluateChange} disabled={!changeId}>
          2) Evaluate
        </button>
        <button onClick={executeChange} disabled={!changeId || !evaluation}>
          3) Execute
        </button>
      </div>

      {changeId && <p style={{ marginTop: "1rem" }}>Change ID: {changeId}</p>}
      {error && <p style={{ marginTop: "0.75rem", color: "#b00020" }}>{error}</p>}

      {evaluation && (
        <DecisionPanel
          decision={evaluation.decision}
          riskScore={evaluation.risk_score}
          explanation={evaluation.explanation}
          constraints={evaluation.constraints}
          telemetrySourceStatus={evaluation.telemetry_source_status}
          metadataSourceStatus={evaluation.metadata_source_status}
        />
      )}

      {execution && (
        <section style={{ border: "1px solid #ddd", padding: "1rem", marginTop: "1rem" }}>
          <h3>Execution Result</h3>
          <p>
            <strong>Status:</strong> {execution.status}
          </p>
          <p>
            <strong>Mode:</strong> {execution.execution_mode}
          </p>
        </section>
      )}

      {timeline.length > 0 && (
        <section style={{ marginTop: "1rem" }}>
          <h3>Execution Timeline</h3>
          <ul>
            {timeline.map((event, idx) => (
              <li key={`${event.created_at}-${idx}`}>
                [{event.created_at}] {event.event_type} - {event.stage}
                {event.payload?.status ? ` (${String(event.payload.status)})` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
