#!/usr/bin/env bash
set -euo pipefail

APP_PASSWORD_FILE="${APP_DATA_DIR}/.app_password"

generate_password() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import secrets,string; chars=string.ascii_letters+string.digits; print(''.join(secrets.choice(chars) for _ in range(24)))"
    return
  fi
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24 | cut -c1-24
    return
  fi
  head -c 128 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-24
}

if [ -f "${APP_PASSWORD_FILE}" ]; then
  APP_PASSWORD="$(tr -d '[:space:]' < "${APP_PASSWORD_FILE}")"
else
  APP_PASSWORD=""
fi

if [ "${#APP_PASSWORD}" -lt 12 ]; then
  mkdir -p "${APP_DATA_DIR}"
  APP_PASSWORD="$(generate_password)"
  printf '%s' "${APP_PASSWORD}" > "${APP_PASSWORD_FILE}"
fi
chmod 600 "${APP_PASSWORD_FILE}"

echo "APP_PASSWORD=${APP_PASSWORD}"
echo "APP_LNDG_PORT=8889"
