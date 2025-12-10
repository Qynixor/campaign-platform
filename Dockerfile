# Use a stable Python base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for psycopg2/postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Collect static files during build
RUN python manage.py collectstatic --noinput

# Expose a default port for environments that don't use $PORT
ENV PORT=8000

# Start Gunicorn (fallback to port 8000 if $PORT is missing)
CMD ["sh", "-c", "gunicorn buskx.wsgi:application --bind 0.0.0.0:${PORT}"]
