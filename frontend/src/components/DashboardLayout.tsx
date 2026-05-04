"use client";

import Link from "next/link";
import { ActivitySquare, ClipboardCheck, FileClock, Gavel, PlusCircle, Rocket, ShieldCheck, Trophy } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { isPlatformAdmin } from "@/lib/auth";

export function DashboardLayout({
  title,
  eyebrow = "Seller dashboard",
  children,
}: {
  title: string;
  eyebrow?: string;
  children: React.ReactNode;
}) {
  const { user } = useAuth();
  const isAdmin = isPlatformAdmin(user);

  return (
    <main className="page-shell dashboard-shell">
      <section className="page-heading">
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
      </section>
      <nav className="dashboard-tabs" aria-label="Dashboard">
        <Link href="/dashboard">
          <Gavel size={17} aria-hidden="true" />
          Auctions
        </Link>
        <Link href="/dashboard/auctions/new">
          <PlusCircle size={17} aria-hidden="true" />
          New auction
        </Link>
        <Link href="/dashboard/lots/new">
          <PlusCircle size={17} aria-hidden="true" />
          New lot
        </Link>
        <Link href="/dashboard/winners">
          <Trophy size={17} aria-hidden="true" />
          Winners
        </Link>
        <Link href="/dashboard/fulfillment">
          <ClipboardCheck size={17} aria-hidden="true" />
          Fulfillment
        </Link>
        {isAdmin ? (
          <>
            <Link href="/dashboard/operations">
              <ActivitySquare size={17} aria-hidden="true" />
              Operations
            </Link>
            <Link href="/dashboard/admin/outcome-repairs">
              <ShieldCheck size={17} aria-hidden="true" />
              Repairs
            </Link>
            <Link href="/dashboard/admin/release-check">
              <Rocket size={17} aria-hidden="true" />
              Release
            </Link>
            <Link href="/dashboard/audit">
              <FileClock size={17} aria-hidden="true" />
              Audit
            </Link>
          </>
        ) : null}
      </nav>
      {children}
    </main>
  );
}
