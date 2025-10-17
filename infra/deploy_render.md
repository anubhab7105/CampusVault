Render deployment notes (backend):
- Use Docker or Python web service.
- Expose port 8000.
- Create persistent volume for uploaded files (static_uploads).
- Set environment variables: SECRET_KEY, DATABASE_URL (optional).

Vercel deployment (frontend):
- Deploy the `frontend/` directory as static site.
- Set environment variable API_BASE if using a different backend URL.
