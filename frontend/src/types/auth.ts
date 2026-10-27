/** Auth domain types. */

import type { UUID, RoleName } from "./common";
export interface User {
  id: UUID;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  auth_provider: "google" | "otp";
  google_sub?: string | null;
  email_verified_at?: string | null;
  department_id?: UUID | null;
  is_active: boolean;
  last_login_at?: string | null;
  role?: RoleName;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface SignedInUser {
  user: User;
  tokens: TokenPair;
}

export interface LoginState {
  access_token: string | null;
  refresh_token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
}

export interface OAuthState {
  code_verifier: string;
  state: string;
}

export type GoogleAuthorizeResponse = {
  authorize_url: string;
  state: string;
};

export type TeacherOtpRequestResponse = {
  expires_in_seconds: number;
};

export type TeacherOtpVerifyResponse = SignedInUser;
