# Deployment Guide

Frontend: Vercel
- Push frontend folder to a repo and connect Vercel.
- Set environment variable `API_BASE_URL` to your backend URL.

Backend: Render
- Create a new Web Service on Render with branch from repo.
- Add environment variables (from `.env.example`) in Render dashboard.
- Use the start command `npm run start`.
- You can also deploy via Docker (we provide `backend/Dockerfile`) if you prefer container-based deployment.
- (Optional) Add a health check path `/` and configure instance size according to traffic.

CI (recommended)
- GitHub Actions workflow is included at `.github/workflows/ci.yml` to run tests.
- Ensure DB credentials for test service are set in the workflow or use a test DB service.
Database: Railway / PlanetScale
- Create a MySQL instance on Railway or PlanetScale.
- Run `sql/schema.sql` and `sql/seeds.sql` against the DB.
- Add DB connection env vars in Render/Vercel.

Cloudinary
- Create an account, set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_KEY`, `CLOUDINARY_SECRET` on Render.

Other
- For SMS, use Twilio and set credentials in env.
- For email, configure SMTP (SendGrid, Mailgun, or SMTP service).
