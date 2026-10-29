FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN /opt/venv/bin/python src/manage.py collectstatic --noinput

FROM python:3.13-slim AS runtime

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=false \
    DJANGO_DB_PATH=/app/data/db.sqlite3 \
    GUNICORN_WORKERS=2

RUN groupadd --system app \
    && useradd --system --gid app --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/data \
    && chown app:app /app/data

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src ./src
COPY docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint
RUN chmod 0755 /usr/local/bin/backend-entrypoint

USER app

VOLUME ["/app/data"]
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/accounts/login/', timeout=2)"]

ENTRYPOINT ["backend-entrypoint"]
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --chdir src --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS} --access-logfile -"]
