# Use official Python image as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create working directory inside container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port Flask will run on
EXPOSE 5050

# Set file permissions for writable files/folders
RUN touch /app/users.json /app/context.json && \
    chmod -R 777 /app/users.json /app/context.json /app/data/health_check /app/data/meter_health_score /app/data/meter_snapshots /app/data/anon_meter_health_score /app/data/offline_meter_health_score /app/data/anon_meter_snapshots /app/data/offline_meter_snapshots

# Default command to run the app
CMD ["python", "app.py"]
