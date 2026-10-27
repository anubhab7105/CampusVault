/** Main app shell: router + error boundary + toasts. */

import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Suspense, lazy } from "react";
import { ErrorBoundary } from "@components/error-boundary/ErrorBoundary";
import { ToastContainer } from "@components/ui/index";
import { AuthLayout } from "@layouts/index";
import { DashboardLayout } from "@layouts/index";
import { routes, type RouteConfig } from "@routes/index";
import { ProtectedRoute } from "@routes/ProtectedRoute";

import "./styles/index.css";

const LoginPage = lazy(() => import("@pages/auth/Login"));

function AppContent() {
  const router = createBrowserRouter([
    {
      path: "/login",
      element: (
        <AuthLayout>
          <Suspense fallback={null}>
            <LoginPage />
          </Suspense>
        </AuthLayout>
      ),
    },
    {
      path: "/",
      element: (
        <DashboardLayout>
          <Suspense fallback={null}>
            <ProtectedRoute>
              <Outlet />
            </ProtectedRoute>
          </Suspense>
        </DashboardLayout>
      ),
      children: routes.filter((r: RouteConfig) => r.path !== "/login"),
    },
  ]);

  return (
    <ErrorBoundary fallback={({ error, reset }) => DefaultFallback({ error, reset })}>
      <ToastContainer />
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}

function DefaultFallback({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-100 p-4 text-center">
      <div className="max-w-md">
        <h2 className="text-body-lg font-semibold text-ink-default">Something went wrong</h2>
        <p className="text-body-sm text-ink-secondary mt-2">{error.message}</p>
        <button onClick={reset} className="mt-4 px-4 py-2 text-brand font-medium hover:underline">
          Try again
        </button>
      </div>
    </div>
  );
}

export default AppContent;

const Outlet = () => null;
