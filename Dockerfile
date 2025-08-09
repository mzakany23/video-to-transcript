# Multi-stage build for transcription services
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install common system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared services library
COPY services/ ./services/

# Copy requirements and install dependencies
COPY requirements/prod.txt ./requirements/prod.txt
RUN pip install --no-cache-dir -r requirements/prod.txt

# Install services in development mode so imports work
COPY pyproject.toml ./
RUN pip install -e .

# Worker service build
FROM base as worker

# Install worker-specific system dependencies (ffmpeg for audio processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy worker code
COPY worker/ ./worker/

# Set working directory to worker
WORKDIR /app/worker

# Run the worker
CMD ["python", "main.py"]

# Webhook service build
FROM base as webhook

# Copy webhook code  
COPY webhook/ ./webhook/

# Install webhook-specific dependencies
RUN pip install functions-framework==3.* google-cloud-run==0.* flask==2.*

# Set working directory to webhook
WORKDIR /app/webhook

# Expose port for webhook
EXPOSE 8080

# Run the webhook
CMD ["python", "main.py"]