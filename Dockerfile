FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies including WeasyPrint requirements
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libpq-dev \
    libffi-dev \
    shared-mime-info \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Default command
CMD ["gunicorn", "analyst.wsgi:application", "--bind", "0.0.0.0:8000"]