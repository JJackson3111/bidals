"use client";

import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Rocket } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { StatusPill } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { ReadinessCheck, ReadinessReport } from "@/lib/types";

export default function ReleaseCheckPage() {
  const [report, setReport] = useState<ReadinessReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      setReport(await api.getReleaseCheck());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load release readiness report.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const groupedChecks = useMemo(() => groupChecks(report?.checks ?? []), [report]);

  return (
    <ProtectedRoute adminOnly>
      <DashboardLayout title="Release readiness" eyebrow="Admin operations">
        <section className="filter-panel operations-filter-panel" aria-label="Release check controls">
          <Rocket size={18} aria-hidden="true" />
          <button className="secondary-button" type="button" onClick={() => void load()} disabled={isLoading}>
            <RefreshCw size={17} aria-hidden="true" />
            Refresh report
          </button>
        </section>

        {isLoading ? <LoadingState label="Loading release readiness" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!isLoading && !error && report ? (
          <>
            <section className="metric-grid operations-metrics" aria-label="Release summary">
              <article className="metric-card">
                <StatusPill status="pass" />
                <span>Pass</span>
                <strong>{report.summary.pass}</strong>
              </article>
              <article className="metric-card">
                <StatusPill status="warn" />
                <span>Warn</span>
                <strong>{report.summary.warn}</strong>
              </article>
              <article className="metric-card">
                <StatusPill status="fail" />
                <span>Fail</span>
                <strong>{report.summary.fail}</strong>
              </article>
            </section>

            <p className="ops-generated">
              Generated {formatDateTime(report.generated_at)} for {report.environment}.
            </p>

            {Object.entries(groupedChecks).length === 0 ? (
              <EmptyState title="No checks" message="Release readiness checks will appear here." />
            ) : (
              Object.entries(groupedChecks).map(([category, checks]) => (
                <section className="dashboard-section" key={category}>
                  <div className="section-heading">
                    <div>
                      <span className="eyebrow">{category}</span>
                      <h2>{humanCategory(category)}</h2>
                    </div>
                  </div>
                  <div className="release-check-list">
                    {checks.map((check) => (
                      <article className="release-check-row" key={`${check.category}-${check.name}`}>
                        <div>
                          <strong>{check.name}</strong>
                          <span>{check.message}</span>
                        </div>
                        <StatusPill status={check.status.toLowerCase()} />
                      </article>
                    ))}
                  </div>
                </section>
              ))
            )}
          </>
        ) : null}
      </DashboardLayout>
    </ProtectedRoute>
  );
}

function groupChecks(checks: ReadinessCheck[]) {
  return checks.reduce<Record<string, ReadinessCheck[]>>((groups, check) => {
    groups[check.category] = [...(groups[check.category] ?? []), check];
    return groups;
  }, {});
}

function humanCategory(category: string) {
  return category.replace(/_/g, " ");
}
