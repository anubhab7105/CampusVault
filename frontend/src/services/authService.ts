/** Auth service layer — thin wrapper over the Axios client. */

import { apiClient } from "@services/apiClient";
import type { GoogleAuthorizeResponse } from "@types/auth";

export const authService = {
  /** Builds the Google OAuth authorize URL for the SPA consent step. */
  googleAuthorize: async (state: string): Promise<GoogleAuthorizeResponse> => {
    const { data } = await apiClient.get<{
      success: boolean;
      message: string;
      data: GoogleAuthorizeResponse;
    }>(`/auth/google/authorize?state=${encodeURIComponent(state)}`);
    return data.data;
  },

  /** Exchange consent-screen code for CampusVault tokens. */
  googleCallback: async (code: string) => {
    const { data } = await apiClient.post<{
      success: boolean;
      message: string;
      data: { tokens: { access_token: string; refresh_token: string }; user: any };
    }>("/auth/google", { code });
    return data.data;
  },

  /** Teacher: request OTP (phase 1). */
  requestTeacherOtp: async (email: string) => {
    const { data } = await apiClient.post<{
      success: boolean;
      message: string;
      data: { expires_in_seconds: number };
    }>("/auth/teachers/otp/request", { email });
    return data.data;
  },

  /** Teacher: verify OTP → tokens (phase 2). */
  verifyTeacherOtp: async (email: string, code: string) => {
    const { data } = await apiClient.post<{
      success: boolean;
      message: string;
      data: { tokens: { access_token: string; refresh_token: string }; user: any };
    }>("/auth/teachers/otp/verify", { email, code });
    return data.data;
  },

  /** Rotate the refresh token. */
  refresh: async () => {
    const { data } = await apiClient.post<{
      success: boolean;
      message: string;
      data: { tokens: { access_token: string; refresh_token: string } };
    }>("/auth/refresh", {});
    return data.data.tokens;
  },

  /** Revoke the refresh token server-side + local logout. */
  logout: async () => {
    try {
      await apiClient.post("/auth/logout", {});
    } catch {
      /* ignore — logout is local regardless of network */
    }
  },

  /** Echo identity + claims from the access token. */
  me: async () => {
    const { data } = await apiClient.get<{
      success: boolean;
      message: string;
      data: { id: string; role: string; permissions: string[] };
    }>("/auth/me");
    return data.data;
  },
};
