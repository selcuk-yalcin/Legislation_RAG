# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python files first
COPY *.py .

# Copy data directory
COPY data/ ./data/

# Copy remaining files
COPY . .

# Verify data is copied
RUN ls -la data/ && echo "Data directory contents:" && find data/ -name "*.pdf" | wc -l

# Make start script executable
RUN chmod +x start.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Start with bash script
CMD ["./start.sh"]
