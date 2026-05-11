# ── Stage 1: frontend builder (placeholder for SPA artifacts) ─────────────────
FROM alpine:3.21 AS frontend-builder
WORKDIR /workspace
RUN mkdir -p /frontend-dist

# ── Stage 2: python dependencies ──────────────────────────────────────────────
FROM python:3.13-alpine AS python-deps
RUN apk add --no-cache g++ gfortran linux-headers libffi-dev rust cargo openssl-dev pkgconf make openblas-dev lapack-dev
WORKDIR /lndg
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt supervisor whitenoise

# ── Stage 3: final (rootless) ──────────────────────────────────────────────────
FROM python:3.13-alpine AS final
# Note: any volume mounted at /lndg/data must be writable by the 'lndg' user
# (UID/GID created here). Adjust host ownership accordingly before first start.
RUN apk add --no-cache libffi openssl && \
    adduser -D -h /lndg lndg
COPY --from=python-deps /install /usr/local
WORKDIR /lndg
COPY --chown=lndg:lndg . .
COPY --chown=lndg:lndg --from=frontend-builder /frontend-dist /lndg/gui/static/spa
USER lndg
ENV PYTHONUNBUFFERED=1
