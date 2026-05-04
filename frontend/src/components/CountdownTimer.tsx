"use client";

import { useEffect, useState } from "react";
import { Clock3 } from "lucide-react";

import { getTimeRemaining } from "@/lib/format";

export function CountdownTimer({ endTime }: { endTime: string }) {
  const [label, setLabel] = useState(() => getTimeRemaining(endTime));

  useEffect(() => {
    const interval = window.setInterval(() => {
      setLabel(getTimeRemaining(endTime));
    }, 1000);

    return () => window.clearInterval(interval);
  }, [endTime]);

  return (
    <span className="countdown">
      <Clock3 size={15} aria-hidden="true" />
      {label}
    </span>
  );
}

