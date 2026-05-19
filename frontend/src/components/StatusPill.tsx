export function StatusPill({ label, status }: { label?: string; status: string }) {
  return <span className={`status-pill status-${status}`}>{label ?? status}</span>;
}
