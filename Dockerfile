# Use the official Python 3.10 slim image
FROM python:3.10-slim

# Set the working directory to /home/site/wwwroot (Standard for Azure)
WORKDIR /home/site/wwwroot

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt from your root into the container
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else from your project into the container
COPY . .

# Expose port 8000 for FastAPI
EXPOSE 8000

# Run uvicorn. 
# We use 'app.main:app' because your main.py is inside the 'app/' folder.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]