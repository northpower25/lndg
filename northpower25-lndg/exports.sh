#!/usr/bin/env bash
set -euo pipefail

APP_PASSWORD_FILE="${APP_DATA_DIR}/.app_password"
if [ -f "${APP_PASSWORD_FILE}" ]; then
  APP_PASSWORD="$(cat "${APP_PASSWORD_FILE}")"
else
  mkdir -p "${APP_DATA_DIR}"
  APP_PASSWORD="$(python3 -c "import secrets,string; chars=string.ascii_letters+string.digits; print(''.join(secrets.choice(chars) for _ in range(24)))")"
  printf '%s' "${APP_PASSWORD}" > "${APP_PASSWORD_FILE}"
  chmod 600 "${APP_PASSWORD_FILE}"
fi

echo "APP_PASSWORD=${APP_PASSWORD}"
echo "APP_LNDG_PORT=8889"
