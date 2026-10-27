/** NotFound placeholder — 404 recovery. */

import { useNavigate } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@components/ui/index";

export default function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-100 px-4 py-12">
      <Card className="max-w-md w-full text-center">
        <CardHeader>
          <CardTitle className="text-6xl font-bold text-ink-default">404</CardTitle>
          <p className="text-body-sm text-ink-secondary">Page not found.</p>
        </CardHeader>
        <CardContent>
          <Button onClick={() => navigate("/")} className="w-full">
            Return to dashboard
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
