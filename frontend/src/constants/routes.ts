/** Route path constants — single source of truth for navigation. */

export const PATHS = {
  LOGIN: "/login",
  DASHBOARD: "/",
  LIBRARY: "/library",
  CHAT: "/chat",
  ADMIN: "/admin",
  NOTIFICATIONS: "/notifications",
  NOT_FOUND: "/not-found",
} as const;

export type RoutePath = (typeof PATHS)[keyof typeof PATHS];
