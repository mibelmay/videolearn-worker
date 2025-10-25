FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH $WORKDIR

RUN pip install --upgrade pip

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

EXPOSE 8080

CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]