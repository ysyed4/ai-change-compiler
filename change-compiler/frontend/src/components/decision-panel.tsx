type DecisionPanelProps = {
  decision: string;
  riskScore: number;
  explanation: string[];
  constraints: string[];
  telemetrySourceStatus: string;
  metadataSourceStatus: string;
};

export function DecisionPanel({
  decision,
  riskScore,
  explanation,
  constraints,
  telemetrySourceStatus,
  metadataSourceStatus,
}: DecisionPanelProps) {
  return (
    <section style={{ border: "1px solid #ddd", padding: "1rem", marginTop: "1rem" }}>
      <h3>Evaluation Decision</h3>
      <p>
        <strong>Decision:</strong> {decision}
      </p>
      <p>
        <strong>Risk Score:</strong> {riskScore}
      </p>
      <p>
        <strong>Telemetry Source:</strong> {telemetrySourceStatus}
      </p>
      <p>
        <strong>Metadata Source:</strong> {metadataSourceStatus}
      </p>
      <h4>Explanation</h4>
      <ul>{explanation.map((item) => <li key={item}>{item}</li>)}</ul>
      <h4>Constraints</h4>
      <ul>{constraints.map((item) => <li key={item}>{item}</li>)}</ul>
    </section>
  );
}
