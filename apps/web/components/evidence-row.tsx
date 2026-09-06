import type { ReactNode } from "react";

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "Not available";
  if (typeof value === "string") return value;
  if (typeof value === "number") return Number.isFinite(value) ? value.toLocaleString() : "Not available";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return JSON.stringify(value);
}

function flattenRecord(record: Record<string, unknown>, prefix = ""): Array<[string, unknown]> {
  return Object.entries(record).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return flattenRecord(value as Record<string, unknown>, path);
    }
    return [[path, value]] as Array<[string, unknown]>;
  });
}

function readableLabel(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function EvidenceRow({ label, value, detail }: { label: string; value: ReactNode; detail?: ReactNode }) {
  return (
    <div className="evidence-row">
      <dt>{label}</dt>
      <dd><strong>{value}</strong>{detail && <span>{detail}</span>}</dd>
    </div>
  );
}

export function EvidenceList({ record }: { record: Record<string, unknown> }) {
  const entries = flattenRecord(record);
  return (
    <dl className="evidence-list">
      {entries.length === 0 ? <EvidenceRow label="Evidence" value="No fields recorded" /> : entries.map(([key, value]) => <EvidenceRow key={key} label={readableLabel(key)} value={formatValue(value)} />)}
    </dl>
  );
}

export function RawEvidence({ value }: { value: unknown }) {
  return (
    <details className="raw-evidence">
      <summary>View raw evidence JSON</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}
