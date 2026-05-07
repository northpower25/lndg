# ── Stage 1: python dependencies ──────────────────────────────────────────────
FROM python:3.13-alpine AS python-deps
RUN apk add --no-cache g++ linux-headers libffi-dev rust cargo openssl-dev pkgconf make
WORKDIR /lndg
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt supervisor whitenoise

# ── Stage 2: final (rootless) ──────────────────────────────────────────────────
FROM python:3.13-alpine AS final
RUN apk add --no-cache libffi openssl && \
    adduser -D -h /lndg lndg
COPY --from=python-deps /install /usr/local
WORKDIR /lndg
COPY --chown=lndg:lndg . .
USER lndg
ENV PYTHONUNBUFFERED=1