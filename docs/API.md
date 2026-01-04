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
- GET /api/documents/:id/view → viewable link for document (students limited to public docs)
- GET /api/documents/admin/all → admin only: list all uploads

Comments
- POST /api/comments/:documentId { body } → authenticated users (students/faculty)
- GET /api/comments/:documentId → list comments
- DELETE /api/comments/:id → admin or comment author

Notes
- Use Authorization: Bearer <token> header for protected routes.
- File uploads stream to Cloudinary; metadata stored in `documents` table.
