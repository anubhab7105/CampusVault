FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y build-essential libssl-dev --no-install-recommends && rm -rf /var/lib/apt/lists/*

# copy
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app

# create runtime directories
RUN mkdir -p /app/app/static_uploads /app/data

EXPOSE 8000

ENV FLASK_APP=app.main
ENV FLASK_RUN_PORT=8000
CMD ["python", "-u", "app/main.py"]
