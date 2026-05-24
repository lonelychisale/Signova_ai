FROM python:3.10-slim

# ✅ Install system tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# ✅ VERY IMPORTANT: install build tools FIRST (separate step)
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir setuptools==68.0.0 wheel

# ✅ Now install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Run app
CMD ["gunicorn", "signova_ai.wsgi:application", "--bind", "0.0.0.0:$PORT"]