FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for compiling some python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project configuration files
COPY pyproject.toml ./

# Install dependencies (installing directly in system python to save space in container)
RUN pip install --no-cache-dir .[dev]

# Copy the rest of the application code
COPY . .

# Expose the API port
EXPOSE 8000

# Run the API server
CMD ["python", "-m", "src.cli", "serve"]
