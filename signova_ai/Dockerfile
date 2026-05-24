FROM python:3.10-slim

# ✅ Install minimal dependencies + ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# ✅ Upgrade tools
RUN pip install --upgrade pip setuptools wheel

# ✅ Install dependencies (no cache to reduce size)
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Run app
CMD ["gunicorn", "signova_ai.wsgi:application", "--bind", "0.0.0.0:$PORT"]
