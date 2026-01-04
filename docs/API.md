# CampusVault API Overview

Base URL: /api

Auth
- POST /api/auth/request-otp { phone } → sends OTP to phone (Twilio)
- POST /api/auth/verify-otp { phone, code, fullName, collegeId, email, password? } → creates user and verifies phone
- POST /api/auth/login { email, password } → returns JWT

Users
- GET /api/users → admin only, list users

Documents
- POST /api/documents (multipart/form-data) { file, title, description, isPublic } → faculty only
- GET /api/documents → list documents (public and private depending on role)

Comments
- POST /api/comments/:documentId { body } → authenticated users (students/faculty)
- GET /api/comments/:documentId → list comments

Notes
- Use Authorization: Bearer <token> header for protected routes.
- File uploads stream to Cloudinary; metadata stored in `documents` table.
