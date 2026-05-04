"use client";

import Link from "next/link";
import { ShieldAlert } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { canManageAuctions, isPlatformAdmin } from "@/lib/auth";

export function ProtectedRoute({
  children,
  adminOnly = false,
  sellerOnly = false,
}: {
  children: React.ReactNode;
  adminOnly?: boolean;
  sellerOnly?: boolean;
}) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <main className="page-shell"><div className="state-panel">Checking access</div></main>;
  }

  const allowed = user && (!adminOnly || isPlatformAdmin(user)) && (!sellerOnly || canManageAuctions(user));
  if (!allowed) {
    const accessLabel = adminOnly
      ? "Use an admin account to open this area."
      : sellerOnly
        ? "Use a seller or admin account to open this area."
        : "Login to open this area.";
    return (
      <main className="page-shell">
        <div className="state-panel error">
          <ShieldAlert size={24} aria-hidden="true" />
          <strong>Access required</strong>
          <span>{accessLabel}</span>
          <Link className="primary-button" href="/login">Login</Link>
        </div>
      </main>
    );
  }

  return <>{children}</>;
}
