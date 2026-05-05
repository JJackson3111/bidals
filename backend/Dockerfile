FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements-prod.txt

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

COPY --chown=app:app . .

RUN DJANGO_SETTINGS_MODULE=bidals.settings.prod \
    DJANGO_SECRET_KEY=build-time-secret \
    DJANGO_ALLOWED_HOSTS=localhost \
    DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000 \
    DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:3000 \
    python manage.py collectstatic --noinput

EXPOSE 8000

USER app

CMD sh -c "python manage.py migrate && gunicorn bidals.wsgi:application --bind 0.0.0.0:$PORT"