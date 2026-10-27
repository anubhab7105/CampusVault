/** ProtectedRoute — redirects to /login when the access token is absent. */

import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@stores/useAuthStore";

export const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, loading } = useAuthStore();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-100">
        <div className="animate-pulse rounded-full h-10 w-10 bg-surface-200" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={"/login"} state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
