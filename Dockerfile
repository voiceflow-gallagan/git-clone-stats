# Build stage
FROM python:3.11-slim AS builder

# Set build-time environment variables
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install uv for fast dependency installation
RUN pip install uv

# Copy dependency files first for better layer caching
COPY requirements.txt pyproject.toml ./

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies using uv (significantly faster than pip)
RUN uv pip install -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=3159 \
    DATABASE_PATH=/app/data/github_stats.db

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY git_clone_stats/ ./git_clone_stats/
COPY main.py ./

# Create data directory for SQLite (running as root, so no permission issues)
RUN mkdir -p /app/data

# Note: Running as root for reliable file system access in containerized environments

# Expose port (defaults to 8080, configurable via PORT env var)
EXPOSE 3159

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-3159}/api/stats').read()"

# Run the application
CMD ["python", "main.py"]
