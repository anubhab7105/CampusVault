/** Login page — unified entry for Student (Google OAuth) + Teacher (OTP). */

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { authService } from "@services/authService";
import { useAuthStore } from "@stores/useAuthStore";
import { useToast } from "@hooks/useToast";
import {
  Button,
  Input,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@components/ui/index";
import { cn } from "@utils/cn";
import { PATHS } from "@constants/routes";

const teacherSchema = z.object({
  email: z.string().email("Enter a valid college email address."),
  code: z.string().min(6, "Code must be 6 digits").max(6),
});

type TeacherForm = z.infer<typeof teacherSchema>;

export default function Login() {
  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();
  const { toast } = useToast();
  const [phase, setPhase] = useState<"provider" | "teacher" | "verifying">("provider");
  const [pending, setPending] = useState(false);

  const form = useForm<TeacherForm>({
    resolver: zodResolver(teacherSchema),
    defaultValues: { email: "", code: "" },
  });

  const handleGoogle = async (e: React.FormEvent) => {
    e.preventDefault();
    setPending(true);
    try {
      // Provider-consent URL — in production the SPA opens this in a browser context.
      const data = await authService.googleAuthorize("init");
      // Scaffold note: Google consent-screen flow completes at /auth/google?code=…
      navigate(`${PATHS.LOGIN}?google_authorize_url=${encodeURIComponent(data.authorize_url)}`);
    } catch (err: any) {
      error("Sign-in failed", err?.campusvaultError?.message ?? String(err ?? ""));
    } finally {
      setPending(false);
    }
  };

  const handleOtpRequest = async (values: TeacherForm) => {
    setPending(true);
    try {
      const { expires_in_seconds } = await authService.requestTeacherOtp(values.email);
      setPhase("verifying");
      success("Code sent", `Expires in ${expires_in_seconds} seconds.`);
    } catch (err: any) {
      error("Could not send code", err?.campusvaultError?.message ?? String(err ?? ""));
    } finally {
      setPending(false);
    }
  };

  const handleOtpVerify = async (values: TeacherForm) => {
    setPending(true);
    try {
      const result = await authService.verifyTeacherOtp(values.email, values.code);
      setTokens(result.tokens.access_token, result.tokens.refresh_token);
      setUser(result.user);
      navigate(PATHS.DASHBOARD, { replace: true });
    } catch (err: any) {
      form.setError("code", { message: err?.campusvaultError?.message ?? "Invalid or expired code." });
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-100 px-4 py-12 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="text-heading-lg font-semibold tracking-tight text-ink-default">CampusVault</h2>
          <p className="mt-2 text-body-md text-ink-secondary">Sign in to your academic library.</p>
        </div>

        <Card className={cn("w-full", phase === "provider" ? "pt-6" : "pt-0")}>
          <CardHeader>
            <CardTitle>{phase === "provider" ? "Sign in" : "Teacher verification"}</CardTitle>
            <CardDescription>
              {phase === "provider"
                ? "Students sign in with Google. Teachers use email OTP."
                : "Enter the code sent to your college email."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {phase === "provider" ? (
              <>
                <Button
                  onClick={handleGoogle}
                  disabled={pending}
                  className="w-full justify-center"
                  variant="default"
                  isLoading={pending}
                >
                  Continue with Google
                </Button>
                <p className="mt-4 text-caption-xs text-ink-tertiary">
                  College Google Workspace account required.
                </p>
              </>
            ) : (
              <form onSubmit={form.handleSubmit(handleOtpRequest)} className="space-y-4">
                <Input
                  label="College email"
                  type="email"
                  placeholder="name@college.edu"
                  {...form.register("email")}
                />
                <Button type="submit" disabled={pending} isLoading={pending} className="w-full">
                  Send verification code
                </Button>
              </form>
            )}
            {phase === "verifying" && (
              <form onSubmit={form.handleSubmit(handleOtpVerify)} className="mt-6 space-y-4">
                <Input label="6-digit code" {...form.register("code")} />
                <Button type="submit" disabled={pending} isLoading={pending} className="w-full">
                  Verify &amp; sign in
                </Button>
              </form>
            )}
          </CardContent>
          <CardFooter className="flex flex-col gap-3 pt-6 border-t">
            {phase === "provider" ? (
              <Button
                type="button"
                onClick={() => setPhase("teacher")}
                variant="ghost"
                className="w-full text-left text-ink-secondary"
              >
                Teacher sign-in with email OTP
              </Button>
            ) : (
              <Button type="button" onClick={() => setPhase("provider")} variant="ghost" className="w-full">
                Back to provider selection
              </Button>
            )}
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
