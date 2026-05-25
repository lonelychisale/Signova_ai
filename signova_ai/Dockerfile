FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir setuptools==69.5.1 wheel

RUN pip install --no-cache-dir -r requirements.txt

CMD gunicorn signova_ai.wsgi:application --bind 0.0.0.0:$PORT