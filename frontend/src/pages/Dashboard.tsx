/** Dashboard placeholder — role-aware overview. */

import { useQuery } from "@tanstack/react-query";
import { authService } from "@services/authService";
import { useAuthStore } from "@stores/useAuthStore";
import { Card, CardContent, CardHeader, CardTitle, Skeleton, EmptyState } from "@components/ui/index";
import { PATHS } from "@constants/routes";

export default function Dashboard() {
  const { user } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authService.me,
    enabled: !!user,
  });

  const roleBadge = (role: string | undefined) => (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-body-xs font-semibold", role === "Admin" ? "bg-amber-100 text-amber-800" : "bg-brand/10 text-brand")}>
      {role ?? "—"}
    </span>
  );

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Card className="h-12"><CardHeader><CardTitle className="text-body-lg">Loading dashboard…</CardTitle></CardHeader><CardContent className="h-24"><Skeleton className="h-full w-3/4" /></CardContent></Card>
        <Card className="h-48"><CardHeader><CardTitle className="text-body-lg">Resources</CardTitle></CardHeader><CardContent className="h-32"><Skeleton className="h-full w-1/2" /></CardContent></Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-heading-lg font-semibold text-ink-default">Dashboard</h1>
          <p className="text-body-sm text-ink-secondary">Welcome back, {user?.full_name}.</p>
        </div>
        <div className="flex items-center gap-2">
          {roleBadge(user?.role)}
          <a href={PATHS.LIBRARY} className="btn-icon" aria-label="Open library">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h18a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
          </a>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>My resources</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-ink-default">{data?.permissions?.length ?? "—"}</p>
            <p className="text-caption-xs text-ink-secondary mt-1">Permissions in your JWT claims.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Last login</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-ink-default">
              {user?.last_login_at ? new Date(user.last_login_at).toLocaleDateString() : "—"}
            </p>
            <p className="text-caption-xs text-ink-secondary mt-1">Auth provider: {user?.auth_provider ?? "—"}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Quick actions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <a href={PATHS.LIBRARY} className="btn-icon w-full justify-start" aria-label="Browse library">
              <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h18a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
              Browse Library
            </a>
            <a href={PATHS.CHAT} className="btn-icon w-full justify-start" aria-label="Open chat">
              <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              Open Chat
            </a>
          </CardContent>
        </Card>
      </div>

      {user?.role !== "Admin" && (
        <EmptyState title="Admin console" description="The Admin section is available to users with the Admin role." />
      )}
    </div>
  );
}
