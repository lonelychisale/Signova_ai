FROM python:3.10

# ✅ Install system dependencies (FFmpeg + build tools)
RUN apt-get update && apt-get install -y ffmpeg build-essential

# ✅ Set working directory
WORKDIR /app

# ✅ Copy all project files into container
COPY . .

# ✅ Upgrade pip + setuptools + wheel (FIXES pkg_resources error)
RUN pip install --upgrade pip setuptools wheel

# ✅ Install Python dependencies
RUN pip install -r requirements.txt

# ✅ Start Django app with Gunicorn
CMD ["gunicorn", "signova_ai.wsgi:application", "--bind", "0.0.0.0:$PORT"]
