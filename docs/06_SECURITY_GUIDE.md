
# Security Guide

## Principles

Assume every request is malicious until validated.

## Authentication

- Google OAuth (Students)
- OTP (Teachers)
- JWT Access Token
- Refresh Token Rotation

## Authorization

RBAC with permission checks.

## API Security

- Rate limiting
- Input validation
- Output encoding
- HTTPS
- Secure headers

## Upload Security

- MIME validation
- Extension whitelist
- File size limits
- Random filenames
- Malware scan pipeline

## Logging

Audit:
- login
- logout
- uploads
- downloads
- admin actions
