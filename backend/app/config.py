import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Database
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///../data/app.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-please")
JWT_ALGORITHM = "HS256"
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "3600"))

# Uploads
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(BASE_DIR, "static_uploads"))
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 32 * 1024 * 1024))  # 32 MB

# Email (SMTP)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "username")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "password")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@example.com")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() in ("1", "true", "yes")

# Admin initial IDs (installer can create)
PRECREATED_ADMINS = os.getenv("PRECREATED_ADMINS", "A001,A002,A003")
