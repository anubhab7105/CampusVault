import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/** Main app shell: router + error boundary + toasts. */
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Suspense, lazy } from "react";
import { ErrorBoundary } from "@components/error-boundary/ErrorBoundary";
import { ToastContainer } from "@components/ui/index";
import { AuthLayout } from "@layouts/index";
import { DashboardLayout } from "@layouts/index";
import { routes } from "@routes/index";
import { ProtectedRoute } from "@routes/ProtectedRoute";
import "./styles/index.css";
const LoginPage = lazy(() => import("@pages/auth/Login"));
function AppContent() {
    const router = createBrowserRouter([
        {
            path: "/login",
            element: (_jsx(AuthLayout, { children: _jsx(Suspense, { fallback: null, children: _jsx(LoginPage, {}) }) })),
        },
        {
            path: "/",
            element: (_jsx(DashboardLayout, { children: _jsx(Suspense, { fallback: null, children: _jsx(ProtectedRoute, { children: _jsx(Outlet, {}) }) }) })),
            children: routes.filter((r) => r.path !== "/login"),
        },
    ]);
    return (_jsxs(ErrorBoundary, { fallback: ({ error, reset }) => DefaultFallback({ error, reset }), children: [_jsx(ToastContainer, {}), _jsx(RouterProvider, { router: router })] }));
}
function DefaultFallback({ error, reset }) {
    return (_jsx("div", { className: "min-h-screen flex items-center justify-center bg-surface-100 p-4 text-center", children: _jsxs("div", { className: "max-w-md", children: [_jsx("h2", { className: "text-body-lg font-semibold text-ink-default", children: "Something went wrong" }), _jsx("p", { className: "text-body-sm text-ink-secondary mt-2", children: error.message }), _jsx("button", { onClick: reset, className: "mt-4 px-4 py-2 text-brand font-medium hover:underline", children: "Try again" })] }) }));
}
export default AppContent;
const Outlet = () => null;
