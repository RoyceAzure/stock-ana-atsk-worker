# syntax=docker/dockerfile:1
# stock-ana-task-worker — GCP Pub/Sub consumer
#
# Build（專案根目錄）:
#   docker build -f deployment/docker/Dockerfile -t ghcr.io/royceazure/stock-ana-atsk-worker:dev-latest .
#
# Run（環境變數由 K8s Secret / ConfigMap 注入，勿將 .env 打包進映像）:
#   docker run --rm --env-file .env ghcr.io/royceazure/stock-ana-atsk-worker:dev-latest

FROM python:3.13-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 映像內不裝測試依賴
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --upgrade pip \
    && /venv/bin/python -c "from pathlib import Path; lines=[l for l in Path('requirements.txt').read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith(('pytest==','pytest-mock=='))]; Path('requirements-prod.txt').write_text('\\n'.join(lines)+'\\n', encoding='utf-8')" \
    && test -s requirements-prod.txt \
    && /venv/bin/pip install --no-cache-dir -r requirements-prod.txt


FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 worker \
    && useradd --uid 1000 --gid worker --shell /usr/sbin/nologin --create-home worker

COPY --from=builder /venv /venv

ENV PATH="/venv/bin:$PATH"

COPY app/ app/
COPY core/ core/
COPY infra/ infra/
COPY models/ models/
COPY service/ service/
COPY strategy/ strategy/
COPY technicals/ technicals/
COPY util/ util/
COPY main.py .

RUN chown -R worker:worker /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WORKER_MODE=consumer

USER worker

STOPSIGNAL SIGTERM

CMD ["python", "main.py", "--mode", "consumer"]
