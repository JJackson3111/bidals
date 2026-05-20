"use client";

import { useEffect, useRef, useState } from "react";
import { Clock3 } from "lucide-react";

type CountdownTimerProps = {
  endTime?: string;
  hideWhenElapsed?: boolean;
  label?: string;
  nowMs?: number | null;
  onElapsed?: () => void;
  targetTime?: string;
};

export function CountdownTimer({
  endTime,
  hideWhenElapsed = true,
  label,
  nowMs,
  onElapsed,
  targetTime,
}: CountdownTimerProps) {
  const resolvedTargetTime = targetTime ?? endTime;
  const [internalNowMs, setInternalNowMs] = useState<number | null>(null);
  const hasNotifiedElapsed = useRef(false);

  useEffect(() => {
    if (nowMs !== undefined) return undefined;

    setInternalNowMs(Date.now());
    const interval = window.setInterval(() => {
      setInternalNowMs(Date.now());
    }, 1000);

    return () => window.clearInterval(interval);
  }, [nowMs]);

  const currentNowMs = nowMs ?? internalNowMs;
  const targetMs = resolvedTargetTime ? new Date(resolvedTargetTime).getTime() : Number.NaN;
  const hasValidTarget = Number.isFinite(targetMs);
  const diffMs = hasValidTarget && currentNowMs !== null ? targetMs - currentNowMs : null;
  const isElapsed = diffMs !== null && diffMs <= 0;

  useEffect(() => {
    hasNotifiedElapsed.current = false;
  }, [resolvedTargetTime]);

  useEffect(() => {
    if (!isElapsed || hasNotifiedElapsed.current) return;
    hasNotifiedElapsed.current = true;
    onElapsed?.();
  }, [isElapsed, onElapsed]);

  if (!resolvedTargetTime || !hasValidTarget) return null;
  if (isElapsed && hideWhenElapsed) return null;

  const remaining = diffMs === null ? "--" : formatCountdown(diffMs);
  const isUrgent = diffMs !== null && diffMs > 0 && diffMs <= 10_000;
  const ariaLabel = label ? `${label} ${remaining}` : remaining;

  return (
    <span
      aria-label={ariaLabel}
      aria-live={isUrgent ? "polite" : "off"}
      className={`countdown ${isUrgent ? "is-urgent" : ""}`}
      role="timer"
    >
      <Clock3 size={15} aria-hidden="true" />
      {label ? <span className="countdown-label">{label}</span> : null}
      <span className="countdown-value">{remaining}</span>
    </span>
  );
}

function formatCountdown(diffMs: number): string {
  const totalSeconds = Math.max(0, Math.ceil(diffMs / 1000));
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${padTime(minutes)}m`;
  if (minutes > 0) return `${minutes}m ${padTime(seconds)}s`;
  return `${seconds}s`;
}

function padTime(value: number): string {
  return value.toString().padStart(2, "0");
}
