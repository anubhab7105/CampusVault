/** Layouts */

import { cn } from "@utils/cn";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@stores/useAuthStore";
import { PATHS } from "@constants/routes";

// Minimal login/shell layout — full viewport, center-aligned card.
export const AuthLayout = ({ children }: { children: React.ReactNode }) => (
  <div className="min-h-screen flex items-center justify-center bg-surface-100 px-4 py-6">
    <div className="max-w-sm w-full">
      {children}
    </div>
  </div>
);

// Full app shell with top header, collapsible sidebar, page outlet.
export const DashboardLayout = ({ children }: { children: React.ReactNode }) => {
  const { collapsed, toggle } = useSidebarStore();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { logout } = useAuthStore();

  return (
    <div className="flex h-screen bg-surface-100">
      <aside className={cn(`fixed inset-y-0 left-0 z-40 w-64 border-r border-border bg-surface-50 transition-transform duration-300 ease-in-out ${collapsed ? "-translate-x-full" : "translate-x-0"}`)} aria-label="Main navigation">
        <div className="flex h-16 items-center justify-between border-b border-border px-4">
          <span className="text-body-lg font-bold tracking-tight text-brand">CampusVault</span>
          <button onClick={toggle} className="p-2 text-muted-foreground hover:text-ink-default" aria-label="Toggle sidebar">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
        </div>
        <nav className="mt-6 px-4 space-y-1" aria-label="Secondary navigation">
          <a href={PATHS.DASHBOARD} className="block px-3 py-2 text-body-sm text-ink-secondary hover:bg-surface-200 rounded-md">Dashboard</a>
          <a href={PATHS.LIBRARY} className="block px-3 py-2 text-body-sm text-ink-secondary hover:bg-surface-200 rounded-md">Library</a>
          <a href={PATHS.CHAT} className="block px-3 py-2 text-body-sm text-ink-secondary hover:bg-surface-200 rounded-md">Chat</a>
          <a href={PATHS.NOTIFICATIONS} className="block px-3 py-2 text-body-sm text-ink-secondary hover:bg-surface-200 rounded-md">Notifications</a>
          {user?.role === "Admin" && (
            <a href={PATHS.ADMIN} className="block px-3 py-2 text-body-sm text-ink-secondary hover:bg-surface-200 rounded-md">Admin</a>
          )}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between border-b border-border bg-surface-50 px-6">
          <h1 className="text-body-lg font-semibold text-ink-default">CampusVault</h1>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(PATHS.NOTIFICATIONS)}
              className="relative p-2 text-muted-foreground hover:text-ink-default"
              aria-label="Notifications"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
              <span className="sr-only">Notifications</span>
            </button>
            <span className="hidden sm:block text-body-sm text-ink-secondary">{user?.full_name ?? "Guest"}</span>
            <button onClick={logout} className="text-body-sm font-medium text-red-600 hover:underline" aria-label="Sign out">
              Sign out
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  </div>
);
