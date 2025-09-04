# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install UV package manager for faster dependency resolution
RUN pip install uv

# Install dependencies
RUN uv pip install --system --no-cache-dir -e .
RUN uv pip install --system --no-cache-dir fastapi[standard] uvicorn pydantic pydantic-extra-types sse-starlette

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN groupadd -r app && useradd -r -g app app

# Create working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY fluidkit/ ./fluidkit/
COPY tests/ ./tests/
COPY docs/ ./docs/
COPY pyproject.toml README.md icon.svg ./

# Install the package in development mode
RUN pip install -e .

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command to run the sample application
CMD ["python", "-m", "uvicorn", "tests.sample.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
