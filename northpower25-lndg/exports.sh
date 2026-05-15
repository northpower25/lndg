#!/bin/bash
# Preserve APP_DATA_DIR when Umbrel already exports it and only fall back to
# UMBREL_APP_DATA_DIR for legacy-compat startup paths that require this bridge.
# The nested default expansion keeps the existing value first, then tries the
# legacy compat variable, and otherwise leaves APP_DATA_DIR empty.
export APP_DATA_DIR="${APP_DATA_DIR:-${UMBREL_APP_DATA_DIR:-}}"
