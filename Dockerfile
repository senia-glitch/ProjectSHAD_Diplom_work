# syntax=docker/dockerfile:1
# The runtime and dev targets share the existing, pinned application packages.
ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder-runtime
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
WORKDIR /build
COPY requirements.lock requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt && pip check

FROM builder-runtime AS builder-dev
RUN pip install -r requirements-dev.txt && pip check

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 \
    PATH="/opt/venv/bin:${PATH}"
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home app
COPY --from=builder-runtime /opt/venv /opt/venv
WORKDIR /srv
COPY --chown=app:app docker/infra.env /srv/.infra.env
COPY --chown=app:app .env.fastbase.example /srv/.env.fastbase
COPY --chown=app:app pyproject.toml models.py run_infrastructure.py ./
COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app config ./config
COPY --chown=app:app scripts ./scripts
RUN mkdir -p /srv/logs /srv/.tmp && chown app:app /srv/logs /srv/.tmp
USER app
EXPOSE 8000
CMD ["python", "-m", "app.main"]

FROM runtime AS dev
COPY --from=builder-dev /opt/venv /opt/venv
COPY --chown=app:app tests ./tests
