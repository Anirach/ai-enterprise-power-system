# ============================================================
# AI POWER SYSTEM - BACKEND DOCKERFILE
# ============================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies including libraries for Docling/image processing
# Added Thai font and OCR support
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libfontconfig1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-tha \
    fonts-thai-tlwg \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with home directory
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m appuser

# Create required directories
RUN mkdir -p /app/uploads /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /app/uploads /home/appuser

# Set home and cache directories for docling/huggingface
ENV HOME=/home/appuser \
    HF_HOME=/home/appuser/.cache/huggingface

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && chmod -R o+r /usr/local/lib/python3.12/site-packages/ \
    && find /usr/local/lib/python3.12/site-packages/ -type d -exec chmod o+rx {} \;

# Copy application code
COPY src/ ./src/

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]


