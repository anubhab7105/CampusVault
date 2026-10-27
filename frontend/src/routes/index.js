import { jsx as _jsx } from "react/jsx-runtime";
/** Route map — lazy-loaded routes with code splitting + route guard. */
import { lazy } from "react-router-dom";
const Login = lazy(() => import("@pages/auth/Login"));
const Dashboard = lazy(() => import("@pages/Dashboard"));
const Library = lazy(() => import("@pages/library/Library"));
const Chat = lazy(() => import("@pages/chat/Chat"));
const Admin = lazy(() => import("@pages/admin/Admin"));
const Notifications = lazy(() => import("@pages/notifications/Notifications"));
const NotFound = lazy(() => import("@pages/NotFound"));
export const routes = [
    { path: "/login", element: _jsx(Login, {}) },
    { path: "/", element: _jsx(Dashboard, {}) },
    { path: "/library", element: _jsx(Library, {}) },
    { path: "/chat", element: _jsx(Chat, {}) },
    { path: "/admin", element: _jsx(Admin, {}) },
    { path: "/notifications", element: _jsx(Notifications, {}) },
    { path: "/not-found", element: _jsx(NotFound, {}) },
    { path: "*", element: _jsx(NotFound, {}) },
];
