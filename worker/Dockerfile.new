# Multi-stage Dockerfile for Worker with Services
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Create working directory
WORKDIR /app

# Copy services package (shared dependency)
COPY services/ ./services/
COPY requirements/prod.txt ./requirements/prod.txt

# Install shared services as package
RUN uv pip install --system -r requirements/prod.txt
RUN uv pip install --system -e .

# Worker-specific stage
FROM base as worker

# Copy worker-specific files
COPY worker/ ./worker/
COPY worker/requirements.txt ./worker/

# Install worker dependencies
RUN uv pip install --system -r worker/requirements.txt

# Set worker as default command
WORKDIR /app/worker
CMD ["python", "main.py"]