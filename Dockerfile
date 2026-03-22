# --- Stage 1: Build dependencies --- 
FROM python:3.9-slim-buster as builder

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for psycopg2 (if using PostgreSQL)
# and other potential packages. Adjust as needed.
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir=/usr/src/app/wheels -r requirements.txt

# --- Stage 2: Final image ---
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Create a non-root user to run the application
RUN adduser --system --group appuser
USER appuser

# Install system dependencies (only runtime ones)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    postgresql-plpython3-16 \ # Added as per request, typically a server-side component
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built wheels from the builder stage
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy the entire Django project into the container
COPY . /app

# Expose the port that Gunicorn will listen on
EXPOSE 8000

# Define environment variables for Django (adjust as needed)
ENV DJANGO_SETTINGS_MODULE moneymoney.settings # Assuming your main settings file is moneymoney/settings.py
ENV PORT 8000

# Run Gunicorn to serve the Django application
# Replace 'moneymoney.wsgi:application' with the actual path to your WSGI application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "moneymoney.wsgi:application"]