# Security Best Practices

- Use HTTPS everywhere (enforce via CLS/hosting settings)
- Store secrets in environment variables and secret stores
- Use strong bcrypt password hashing (cost >= 12)
- Use parameterized queries (Sequelize is used here)
- Use rate limiting and input validation to avoid abuse
- Limit allowed file types and scan uploads in production
- Avoid sending sensitive data in emails
- Rotate secrets and audit logs regularly
