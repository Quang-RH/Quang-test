FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

# Host (Render/Cloud Run/Fly) sẽ inject biến PORT; mặc định 8000 cho local.
ENV PORT=8000
EXPOSE 8000

# Bind 0.0.0.0:$PORT để host truy cập được.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
