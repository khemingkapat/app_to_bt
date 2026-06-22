# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.11-alpine AS builder

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into /app/.venv
RUN uv sync --frozen --no-install-project --no-dev

# Stage 2: Runner
FROM python:3.11-alpine

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code and proto definitions
# server.py expects proto/ and src/ to be in the same parent directory
COPY src/ ./src/
COPY proto/ ./proto/

# Expose port 50051
EXPOSE 50051

# Command to run the worker
CMD ["python", "src/server.py"]
