FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/langgraph.lock /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose port for Studio
EXPOSE 8000

CMD ["python", "-m", "langgraph", "serve"]
