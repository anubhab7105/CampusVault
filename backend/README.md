# CampusVault Backend

Setup:

1. Copy `.env.example` to `.env` and fill in credentials (DB, Cloudinary, SMTP, Twilio)
2. Install deps: `npm install`
3. Setup MySQL DB and run `sql/schema.sql` and `sql/seeds.sql` (or run `npm run db:sync` for development)
4. Run server: `npm run dev`

Notes:
- Uses Sequelize for models. In production, use migrations instead of `sync`.
- JWT auth and role middleware are in `src/middleware`.
- File uploads stream to Cloudinary via `src/routes/documents.js`.
