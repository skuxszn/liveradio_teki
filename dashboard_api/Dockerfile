FROM python:3.11-slim

# Install ffmpeg for video validation
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create stream control directory
RUN mkdir -p /var/run/stream

# Add current directory to Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 9001

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9001"]

