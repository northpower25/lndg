#!/bin/bash
# Preserve APP_DATA_DIR when Umbrel already exports it and only fall back to
# UMBREL_APP_DATA_DIR for legacy-compat startup paths that require this bridge.
export APP_DATA_DIR="${APP_DATA_DIR:-${UMBREL_APP_DATA_DIR:-}}"
