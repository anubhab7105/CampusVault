FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV FLASK_APP=app.main
ENV FLASK_RUN_HOST=0.0.0.0
EXPOSE 8000
CMD ["python", "-m", "app.main"]
