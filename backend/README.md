# Backend (FastAPI) for Online Library

## Setup (local)
1. Create virtualenv:
   python -m venv venv
   source venv/bin/activate

2. Install:
   pip install -r requirements.txt

3. Create uploads folder:
   mkdir -p backend/app/static_uploads

4. Run:
   cd backend
   ./run.sh

The server will run at http://127.0.0.1:8000

## Env
You can set environment variables via `.env`:
- DATABASE_URL (default sqlite:///./data.db)
- SECRET_KEY
- ACCESS_TOKEN_EXPIRE_MINUTES

## Docker
docker build -t online-library-backend:latest -f Dockerfile .
docker run -p 8000:8000 -v $(pwd)/app/static_uploads:/app/app/static_uploads online-library-backend:latest
