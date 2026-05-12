# ── Stage 1: frontend builder (placeholder for SPA artifacts) ─────────────────
FROM alpine:3.21 AS frontend-builder
WORKDIR /workspace
RUN mkdir -p /frontend-dist

# ── Stage 2: python dependencies (base – no ML) ───────────────────────────────
FROM python:3.13-alpine AS python-deps
RUN apk add --no-cache g++ linux-headers libffi-dev rust cargo openssl-dev pkgconf make
WORKDIR /lndg
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt supervisor whitenoise

# ── Stage 2-ML: python dependencies (ML flavor) ───────────────────────────────
FROM python-deps AS python-deps-ml
COPY requirements-ml.txt .
RUN apk add --no-cache gfortran openblas-dev lapack-dev && \
    pip install --no-cache-dir --prefix=/install -r requirements-ml.txt

# ── Stage 3: final (rootless, base – no ML) ───────────────────────────────────
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

# ── Stage 4: final-ml (ML flavor – includes scikit-learn + joblib) ────────────
# Use: docker build --target final-ml -t lndg:latest-ml .
FROM python:3.13-alpine AS final-ml
RUN apk add --no-cache openblas && \
    adduser -D -h /lndg lndg
COPY --from=python-deps-ml /install /usr/local
WORKDIR /lndg
COPY --chown=lndg:lndg . .
COPY --chown=lndg:lndg --from=frontend-builder /frontend-dist /lndg/gui/static/spa
USER lndg
ENV PYTHONUNBUFFERED=1
