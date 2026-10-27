import { jsx as _jsx, Fragment as _Fragment } from "react/jsx-runtime";
/** ProtectedRoute — redirects to /login when the access token is absent. */
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@stores/useAuthStore";
export const ProtectedRoute = ({ children }) => {
    const { isAuthenticated, loading } = useAuthStore();
    const location = useLocation();
    if (loading) {
        return (_jsx("div", { className: "min-h-screen flex items-center justify-center bg-surface-100", children: _jsx("div", { className: "animate-pulse rounded-full h-10 w-10 bg-surface-200" }) }));
    }
    if (!isAuthenticated) {
        return _jsx(Navigate, { to: "/login", state: { from: location }, replace: true });
    }
    return _jsx(_Fragment, { children: children });
};
