# Use Python 3.13
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files with build settings
RUN DJANGO_SETTINGS_MODULE=buskx.settings_build python manage.py collectstatic --noinput

# Use the port provided by Render
CMD gunicorn buskx.wsgi:application --bind 0.0.0.0:$PORT