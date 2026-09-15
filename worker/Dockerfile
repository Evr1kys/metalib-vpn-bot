# Worker Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy backend code (worker depends on it)
COPY backend/app ./backend/app

# Copy worker requirements
COPY worker/requirements.txt ./worker/

# Install Python dependencies
RUN pip install --no-cache-dir -r worker/requirements.txt

# Copy worker application
COPY worker ./worker

# Set PYTHONPATH to include backend directory so 'app' module can be found
ENV PYTHONPATH="${PYTHONPATH}:/app/backend"

# Run Celery worker
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
