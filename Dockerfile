# Build stage - Frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Runtime stage - Backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend
COPY backend/ backend/
COPY config.yaml .
COPY --from=frontend-build /app/frontend/dist frontend/dist/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Create directories
RUN mkdir -p uploads data

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
