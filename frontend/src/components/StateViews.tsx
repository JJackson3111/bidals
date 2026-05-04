import { AlertTriangle, Loader2, PackageOpen } from "lucide-react";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="state-panel" role="status">
      <Loader2 className="spin" size={22} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="state-panel">
      <PackageOpen size={24} aria-hidden="true" />
      <strong>{title}</strong>
      <span>{message}</span>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="state-panel error" role="alert">
      <AlertTriangle size={24} aria-hidden="true" />
      <strong>Something went wrong</strong>
      <span>{message}</span>
    </div>
  );
}

