"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, LogOut, Menu, X } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";
import { canManageAuctions } from "@/lib/auth";

const productNavItems = [
  { href: "/features", label: "Features" },
  { href: "/#how-it-works", label: "How It Works" },
  { href: "/pricing", label: "Pricing" },
];

export function MobileNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const canUseDashboard = canManageAuctions(user);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    setIsMenuOpen(false);
  }, [pathname]);

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

  function isProductNavActive(href: string) {
    if (href === "/features") return pathname === "/features";
    if (href === "/pricing") return pathname === "/pricing";
    return false;
  }

  function renderProductNavLinks() {
    return productNavItems.map((item) => {
      const isActive = isProductNavActive(item.href);

      return (
        <Link
          key={item.href}
          href={item.href}
          className={`nav-product-link ${isActive ? "active" : ""}`}
          onClick={() => setIsMenuOpen(false)}
        >
          <span>{item.label}</span>
        </Link>
      );
    });
  }

  return (
    <header className="mobile-nav">
      <Link href="/" className="brand-link" aria-label="BIDALS home" onClick={() => setIsMenuOpen(false)}>
        <span className="brand-mark">
          <Image className="brand-logo" src="/bidals-logo-mark.png" alt="" width={36} height={36} aria-hidden="true" priority />
        </span>
        <span className="brand-wordmark">BIDALS</span>
      </Link>

      <nav className="product-nav" aria-label="Product navigation">
        {renderProductNavLinks()}
      </nav>

      <nav className="nav-actions" aria-label="Primary navigation">
        <button
          className="nav-menu-button"
          type="button"
          aria-controls="mobile-marketing-navigation"
          aria-expanded={isMenuOpen}
          aria-label={isMenuOpen ? "Close navigation menu" : "Open navigation menu"}
          onClick={() => setIsMenuOpen((current) => !current)}
        >
          {isMenuOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
        </button>
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
        ) : null}
        <Link className="nav-primary-action" href="/book-demo" onClick={() => setIsMenuOpen(false)}>
          Book a demo
        </Link>
        {user ? (
          <button className="nav-logout-button" type="button" onClick={handleLogout} title="Logout" aria-label="Logout">
            <LogOut size={17} aria-hidden="true" />
          </button>
        ) : null}
      </nav>

      {isMenuOpen ? (
        <nav className="mobile-menu-panel" id="mobile-marketing-navigation" aria-label="Mobile marketing navigation">
          {renderProductNavLinks()}
        </nav>
      ) : null}
    </header>
  );
}
