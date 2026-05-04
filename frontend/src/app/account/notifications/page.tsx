"use client";

import { useEffect, useState } from "react";
import { Bell, CheckCheck } from "lucide-react";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { StatusPill } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AccountNotification } from "@/lib/types";

export default function AccountNotificationsPage() {
  const [notifications, setNotifications] = useState<AccountNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.getAccountNotifications();
        setNotifications(response.results);
        setUnreadCount(response.unread_count);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load notifications.");
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, []);

  async function markRead(notification: AccountNotification) {
    if (notification.is_read) return;
    setError(null);
    try {
      const saved = await api.markNotificationRead(notification.id);
      setNotifications((current) => current.map((item) => (item.id === saved.id ? saved : item)));
      setUnreadCount((current) => Math.max(0, current - 1));
      window.dispatchEvent(new Event("bidals:notifications-updated"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to mark notification read.");
    }
  }

  async function markAllRead() {
    setError(null);
    try {
      await api.markAllNotificationsRead();
      setNotifications((current) => current.map((item) => ({ ...item, is_read: true, read_at: item.read_at ?? new Date().toISOString() })));
      setUnreadCount(0);
      window.dispatchEvent(new Event("bidals:notifications-updated"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to mark notifications read.");
    }
  }

  return (
    <ProtectedRoute>
      <main className="page-shell">
        <section className="page-heading">
          <span className="eyebrow">Account</span>
          <h1>Notifications</h1>
          <p>{unreadCount} unread</p>
          {unreadCount > 0 ? (
            <button className="secondary-button" type="button" onClick={() => void markAllRead()}>
              <CheckCheck size={17} aria-hidden="true" />
              Mark all read
            </button>
          ) : null}
        </section>

        {isLoading ? <LoadingState label="Loading notifications" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!isLoading && !error ? (
          notifications.length === 0 ? (
            <EmptyState title="No notifications yet" message="Winner and fulfillment updates will appear here." />
          ) : (
            <div className="dashboard-grid">
              {notifications.map((notification) => (
                <article className={`auction-card management-card ${notification.is_read ? "" : "unread-card"}`} key={notification.id}>
                  <div className="card-topline">
                    <StatusPill status={notification.is_read ? "read" : "unread"} />
                    <span>{formatDateTime(notification.created_at)}</span>
                  </div>
                  <Bell size={22} aria-hidden="true" />
                  <h2>{notification.subject}</h2>
                  <p className="notification-body">{notification.body}</p>
                  {!notification.is_read ? (
                    <button className="secondary-button" type="button" onClick={() => void markRead(notification)}>
                      <CheckCheck size={17} aria-hidden="true" />
                      Mark read
                    </button>
                  ) : null}
                </article>
              ))}
            </div>
          )
        ) : null}
      </main>
    </ProtectedRoute>
  );
}
