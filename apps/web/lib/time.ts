export function currentTime(): number { return Date.now(); }

export function utcTime(value: string | null): string {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Invalid timestamp";
  return `${date.toISOString().replace("T", " ").replace(/\.\d{3}Z$/, "")} UTC`;
}

export function ageText(value: string | null, now: number): string {
  if (!value) return "age unknown";
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return "age unknown";
  const seconds = Math.floor((now - timestamp) / 1000);
  if (seconds < 0) return "timestamp is in the future";
  if (seconds < 60) return "less than 1 minute old";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min old`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hr old`;
  return `${Math.floor(seconds / 86400)} days old`;
}
