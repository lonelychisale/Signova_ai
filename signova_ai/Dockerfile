FROM python:3.10-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    git \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# Upgrade pip tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt
# ✅ Run app
CMD gunicorn signova_ai.wsgi:application --bind 0.0.0.0:${PORT:-8000}