"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, Gavel, LayoutDashboard, LogIn, LogOut, Search, Trophy, UserPlus } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";
import { canManageAuctions } from "@/lib/auth";

const navItems = [
  { href: "/auctions", label: "Browse", icon: Search },
  { href: "/account/won-lots", label: "Won", icon: Trophy, authenticated: true },
  { href: "/account/notifications", label: "Alerts", icon: Bell, authenticated: true },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, protected: true },
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
          <Gavel size={18} aria-hidden="true" />
        </span>
        <span>BIDALS</span>
      </Link>

      <nav className="nav-actions" aria-label="Primary navigation">
        {navItems.map((item) => {
          if (item.authenticated && !user) return null;
          if (item.protected && !canUseDashboard) return null;
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`icon-link ${isActive ? "active" : ""}`}
              title={item.label}
              aria-label={item.label}
            >
              <span className="nav-icon-wrap">
                <Icon size={18} aria-hidden="true" />
                {item.href === "/account/notifications" && unreadCount > 0 ? (
                  <span className="nav-badge" aria-label={`${unreadCount} unread notifications`}>
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                ) : null}
              </span>
              <span>{item.label}</span>
            </Link>
          );
        })}

        {user ? (
          <button className="icon-button" type="button" onClick={handleLogout} title="Logout" aria-label="Logout">
            <LogOut size={18} aria-hidden="true" />
            <span>Logout</span>
          </button>
        ) : (
          <>
            <Link className="icon-link" href="/login" title="Login" aria-label="Login">
              <LogIn size={18} aria-hidden="true" />
              <span>Login</span>
            </Link>
            <Link className="icon-link compact-hide" href="/register" title="Register" aria-label="Register">
              <UserPlus size={18} aria-hidden="true" />
              <span>Register</span>
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
