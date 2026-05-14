#!/bin/bash
# APP_DATA_DIR is provided by umbreld as UMBREL_APP_DATA_DIR when this
# script is sourced during installation/startup.  Export it under the
# legacy name so that docker-compose.yml variable substitution works.
export APP_DATA_DIR="${UMBREL_APP_DATA_DIR}"
