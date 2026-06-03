# ReClaw 2.0 — Production image (Hetzner)
# Start lean. Add CUDA / Ollama layers only when you actually run local LLMs in Analyst or future agents.

FROM python:3.11-slim

WORKDIR /app

# System deps for scraping + yaml
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Non-root
RUN useradd -m -u 1000 reclaw && chown -R reclaw:reclaw /app
USER reclaw

ENV PYTHONPATH=/app
ENV RECLAW_ENV=prod

# Default command runs the API (override for one-off orchestrator runs)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Run as non-root user (security)
RUN useradd -m -u 1000 reclawuser && chown -R reclawuser:reclawuser /app
USER reclawuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=3)" || exit 1
