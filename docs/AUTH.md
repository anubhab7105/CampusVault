# Authentication & OTP Flow

Signup (Single page flow):
1. User provides Full Name, College ID, Email, Phone
2. Client calls POST `/api/auth/request-otp` with phone — server generates 6-digit code, stores in `otps` table with expiry (5 min), and sends SMS via Twilio.
3. User enters OTP — client calls `POST /api/auth/verify-otp` with the code and user details. On success, a user is created and marked verified.
4. If password omitted during verify, server generates temp password, emails user; otherwise user-provided password is used.

Login:
- `POST /api/auth/login` returns a JWT (Bearer) valid for days as configured.

Password Reset:
- `POST /api/auth/request-password-reset` with email → server creates a one-time token emailed to user.
- `POST /api/auth/reset-password` with token + newPassword → resets password.

Security notes:
- Do not disclose whether emails/phones exist in the system for privacy.
- Rate-limit OTP and password reset endpoints to prevent abuse.
