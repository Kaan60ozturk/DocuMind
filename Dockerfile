# ---- Stage 1: build the frontend ----
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime serving the API and the built UI ----
FROM python:3.11-slim AS runtime
WORKDIR /app

COPY backend/ backend/
# Editable install keeps the app importable from /app/backend, so the
# relative path to /app/frontend/dist (static mount) stays valid.
RUN pip install --no-cache-dir -e ./backend

COPY --from=frontend-build /build/dist frontend/dist

RUN useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

ENV DATA_DIR=/app/data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

WORKDIR /app/backend
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
