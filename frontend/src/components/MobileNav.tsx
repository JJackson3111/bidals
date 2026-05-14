"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, LogOut, Search } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";
import { canManageAuctions } from "@/lib/auth";

const productNavItems = [
  { href: "/auctions", label: "Browse", icon: Search },
  { href: "/#how-it-works", label: "How It Works" },
  { href: "/pricing", label: "Pricing" },
];

export function MobileNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const canUseDashboard = canManageAuctions(user);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    let isActive = true;

    async function loadUnreadCount() {
      if (!user) {
        setUnreadCount(0);
        return;
      }

      try {
        const response = await api.getUnreadNotificationCount();
        if (isActive) setUnreadCount(response.unread_count);
      } catch {
        if (isActive) setUnreadCount(0);
      }
    }

    const handleNotificationsUpdated = () => {
      void loadUnreadCount();
    };

    void loadUnreadCount();
    window.addEventListener("bidals:notifications-updated", handleNotificationsUpdated);

    return () => {
      isActive = false;
      window.removeEventListener("bidals:notifications-updated", handleNotificationsUpdated);
    };
  }, [user]);

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  return (
    <header className="mobile-nav">
      <Link href="/" className="brand-link" aria-label="BIDALS home">
        <span className="brand-mark">
          <Image className="brand-logo" src="/bidals-logo-mark.png" alt="" width={36} height={36} aria-hidden="true" priority />
        </span>
        <span className="brand-wordmark">BIDALS</span>
      </Link>

      <nav className="product-nav" aria-label="Product navigation">
        {productNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.href === "/auctions" && (pathname === "/auctions" || pathname.startsWith("/auctions/"));
          return (
            <Link key={item.href} href={item.href} className={`nav-product-link ${isActive ? "active" : ""}`}>
              {Icon ? <Icon size={15} aria-hidden="true" /> : null}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <nav className="nav-actions" aria-label="Primary navigation">
        {user ? (
          <>
            <Link className="nav-utility-link" href="/account/notifications" title="Alerts" aria-label="Alerts">
              <span className="nav-icon-wrap">
                <Bell size={17} aria-hidden="true" />
                {unreadCount > 0 ? (
                  <span className="nav-badge" aria-label={`${unreadCount} unread notifications`}>
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                ) : null}
              </span>
              <span>Alerts</span>
            </Link>
            <Link className="nav-secondary-action auth-dashboard-action" href={canUseDashboard ? "/dashboard" : "/account/won-lots"}>
              {canUseDashboard ? "Dashboard" : "Won lots"}
            </Link>
          </>
        ) : (
          <Link className="nav-secondary-action nav-login-action" href="/login">
            Login
          </Link>
        )}
        <Link className="nav-primary-action" href="/dashboard/auctions/new">
          Start Auction
        </Link>
        {user ? (
          <button className="nav-logout-button" type="button" onClick={handleLogout} title="Logout" aria-label="Logout">
            <LogOut size={17} aria-hidden="true" />
          </button>
        ) : null}
      </nav>
    </header>
  );
}
