FROM node:22.22.2-bookworm-slim AS web-build

WORKDIR /src/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
COPY shared/ /src/shared/
RUN npm run build

# ACIS API image
FROM python:3.11.14-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONPATH=/app

WORKDIR /app

# Lean core deps first (layer cached independently of source changes)
COPY requirements.docker.txt ./
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --disable-pip-version-check --default-timeout=120 --retries=5 \
    --index-url="${PIP_INDEX_URL}" -r requirements.docker.txt

RUN groupadd --system --gid 10001 acis \
    && useradd --system --uid 10001 --gid acis --home-dir /home/acis \
       --create-home --shell /usr/sbin/nologin acis \
    && mkdir -p /app/data \
    && chown -R 10001:10001 /app /home/acis

COPY --chown=10001:10001 . .
COPY --from=web-build --chown=10001:10001 /src/web/dist /app/web/dist

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "acis.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
