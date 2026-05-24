FROM python:3.10

# ✅ install ffmpeg (THIS is what we need)
RUN apt-get update && apt-get install -y ffmpeg

# working directory
WORKDIR /app

# copy project
COPY . .

# install python deps
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# run server
CMD ["gunicorn", "signova_ai.wsgi:application", "--bind", "0.0.0.0:$PORT"]
