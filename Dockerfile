# Global build arg – override in CI to pull the pre-built base image from GHCR
# and skip the expensive compiler stage entirely.  Local builds fall back to
# python-deps-builder (the stage defined below) so no external image is needed.
ARG PYTHON_DEPS_IMAGE=python-deps-builder

# ── Stage 1: frontend builder (placeholder for SPA artifacts) ─────────────────
FROM alpine:3.21 AS frontend-builder
WORKDIR /workspace
RUN mkdir -p /frontend-dist

# ── Stage 2-builder: compile python packages from source ─────────────────────
# This stage is the source of truth used by build-python-deps.yml to produce
# the ghcr.io/<owner>/lndg-python-deps cached base image.
FROM python:3.13-alpine AS python-deps-builder
RUN apk add --no-cache g++ linux-headers libffi-dev rust cargo openssl-dev pkgconf make
WORKDIR /lndg
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt supervisor whitenoise

# ── Stage 2: python dependencies ─────────────────────────────────────────────
# In CI docker-publish.yml sets PYTHON_DEPS_IMAGE to the pre-built GHCR image,
# skipping the compiler stage above.  Default (local builds) references
# python-deps-builder so no registry access is required.
FROM ${PYTHON_DEPS_IMAGE} AS python-deps

# ── Stage 2-ML: python dependencies (ML flavor) ───────────────────────────────
FROM python-deps AS python-deps-ml
COPY requirements-ml.txt .
RUN apk add --no-cache gfortran openblas-dev lapack-dev && \
    pip install --no-cache-dir --prefix=/install -r requirements-ml.txt

# ── Stage 3: final (rootless, base – no ML) ───────────────────────────────────
FROM python:3.13-alpine AS final
# su-exec is used to drop from root to the lndg user after fixing volume ownership at runtime.
RUN apk add --no-cache libffi openssl su-exec && \
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
RUN apk add --no-cache openblas su-exec && \
    adduser -D -h /lndg lndg
COPY --from=python-deps-ml /install /usr/local
WORKDIR /lndg
COPY --chown=lndg:lndg . .
COPY --chown=lndg:lndg --from=frontend-builder /frontend-dist /lndg/gui/static/spa
USER lndg
ENV PYTHONUNBUFFERED=1
