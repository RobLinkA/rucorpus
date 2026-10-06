FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_SITE_NAME=RuCorpus
ARG VITE_SITE_SUBTITLE="Parallel Corpus Search System"
ENV VITE_SITE_NAME=$VITE_SITE_NAME VITE_SITE_SUBTITLE=$VITE_SITE_SUBTITLE
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /build/dist /app/frontend/dist
COPY scripts/container-start.sh /app/container-start.sh
RUN python manage.py collectstatic --noinput \
    && groupadd --system app && useradd --system --gid app app \
    && mkdir -p /state/media && chown -R app:app /state /app \
    && chmod +x /app/container-start.sh
USER app
ENV DJANGO_DEBUG=0 DJANGO_DB_PATH=/state/db.sqlite3 DJANGO_MEDIA_ROOT=/state/media
EXPOSE 8000
ENTRYPOINT ["/app/container-start.sh"]
