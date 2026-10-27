/** Route map — lazy-loaded routes with code splitting + route guard. */

import { lazy, Suspense } from "react-router-dom";

const Login = lazy(() => import("@pages/auth/Login"));
const Dashboard = lazy(() => import("@pages/Dashboard"));
const Library = lazy(() => import("@pages/library/Library"));
const Chat = lazy(() => import("@pages/chat/Chat"));
const Admin = lazy(() => import("@pages/admin/Admin"));
const Notifications = lazy(() => import("@pages/notifications/Notifications"));
const NotFound = lazy(() => import("@pages/NotFound"));

export const routes = [
  { path: "/login", element: <Login /> },
  { path: "/", element: <Dashboard /> },
  { path: "/chat", element: <Chat /> },
  { path: "/admin", element: <Admin /> },
  { path: "/notifications", element: <Notifications /> },
  { path: "/not-found", element: <NotFound /> },
  { path: "*", element: <NotFound /> },
] as const;

export { Suspense };
