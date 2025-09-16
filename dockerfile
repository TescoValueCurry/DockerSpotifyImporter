FROM python:3.11-slim

WORKDIR /app

# Install system dependencies: ffmpeg and git (required by spotdl)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install SpotDL globally
RUN pip install --no-cache-dir spotdl==4.4.0

# Copy your app code
COPY . .

ENV PORT=8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
