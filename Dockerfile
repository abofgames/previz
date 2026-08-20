# Build the UI, then serve it from the Python app so the whole thing is one
# container and one URL.
FROM node:20-slim AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend/ ./backend/
RUN pip install --no-cache-dir .

COPY --from=ui /ui/dist ./frontend/dist

# Cloud Run injects PORT; default keeps `docker run -p 8000:8000` working.
ENV PORT=8000
EXPOSE 8000
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
