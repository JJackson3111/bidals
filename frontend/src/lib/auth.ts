import type { LoginResponse, User } from "@/lib/types";

const ACCESS_TOKEN_KEY = "bidals.accessToken";
const REFRESH_TOKEN_KEY = "bidals.refreshToken";
const USER_KEY = "bidals.user";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;

  const value = window.localStorage.getItem(USER_KEY);
  if (!value) return null;

  try {
    return JSON.parse(value) as User;
  } catch {
    clearAuthSession();
    return null;
  }
}

export function storeAuthSession(session: LoginResponse): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, session.access);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, session.refresh);
  window.localStorage.setItem(USER_KEY, JSON.stringify(session.user));
}

export function storeUser(user: User): void {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function canManageAuctions(user: User | null): boolean {
  return Boolean(user && (user.role === "seller" || isPlatformAdmin(user)));
}

export function isPlatformAdmin(user: User | null): boolean {
  return Boolean(user && (user.is_platform_admin || user.role === "admin"));
}
