import { Icon, type IconName } from "./icon";

type StatusTone = "success" | "warning" | "danger" | "info" | "unknown";

function statusPresentation(status: string): { tone: StatusTone; icon: IconName } {
  const normalized = status.toUpperCase().replaceAll(" ", "_");
  if (["PASS", "STABLE", "SUCCESS", "HEALTHY", "OPERATIONAL", "RESOLVED", "MEASURED"].includes(normalized)) return { tone: "success", icon: "check" };
  if (["WARN", "WARNING", "PARTIAL", "ACKNOWLEDGED", "DEGRADED", "FALLBACK"].includes(normalized)) return { tone: "warning", icon: "warning" };
  if (["FAIL", "FAILED", "ERROR", "DRIFT", "OPEN", "HIGH", "CRITICAL"].includes(normalized)) return { tone: "danger", icon: normalized === "DRIFT" ? "activity" : "x" };
  if (["INFO"].includes(normalized)) return { tone: "info", icon: "info" };
  return { tone: "unknown", icon: ["SKIPPED", "NO_BASELINE", "INSUFFICIENT_HISTORY"].includes(normalized) ? "info" : "warning" };
}

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const presentation = statusPresentation(status);
  return (
    <span className={`status-badge status-${presentation.tone}`} data-status={status}>
      <Icon name={presentation.icon} size={14} />
      <span>{label ?? status}</span>
    </span>
  );
}
