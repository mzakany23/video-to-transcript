# Multi-stage Dockerfile for Webhook with Services
FROM python:3.11-slim as base

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

# Webhook-specific stage  
FROM base as webhook

# Copy webhook-specific files
COPY webhook/ ./webhook/
COPY webhook/requirements.txt ./webhook/

# Install webhook dependencies
RUN uv pip install --system -r webhook/requirements.txt

# Set webhook as default command
WORKDIR /app/webhook
CMD ["functions-framework", "--target=webhook_handler", "--port=8080"]