# Use official Python image as base
FROM python:3.10-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Install build dependencies (optional but good for some Python libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy files
COPY . .

# Expose Flask/gunicorn port
EXPOSE 5050

# Make sure the data folder is readable
RUN mkdir -p /app/data
RUN chmod -R 777 /app/data

# Run app with gunicorn (production-grade WSGI)
CMD ["gunicorn", "-w", "4", "-t", "240", "-b", "0.0.0.0:5050", "app:app"]