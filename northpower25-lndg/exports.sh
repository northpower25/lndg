#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${APP_DATA_DIR:?APP_DATA_DIR is required}"

APP_PASSWORD_FILE="${APP_DATA_DIR}/.app_password"

generate_password() {
  # Keep APP_PASSWORD strictly alphanumeric to avoid escaping issues when the
  # value is rendered in Umbrel compose/templates and login metadata.
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import secrets,string; chars=string.ascii_letters+string.digits; print(''.join(secrets.choice(chars) for _ in range(24)))"
    return
  fi
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 24
    return
  fi
  head -c 64 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24
}

if [ -f "${APP_PASSWORD_FILE}" ]; then
  APP_PASSWORD="$(tr -d '[:space:]' < "${APP_PASSWORD_FILE}")"
else
  APP_PASSWORD=""
fi

if [ "${#APP_PASSWORD}" -ne 24 ]; then
  mkdir -p "${APP_DATA_DIR}"
  APP_PASSWORD="$(generate_password)"
  tmp_file="$(mktemp "${APP_PASSWORD_FILE}.XXXXXX")"
  chmod 600 "${tmp_file}"
  printf '%s' "${APP_PASSWORD}" > "${tmp_file}"
  mv -f "${tmp_file}" "${APP_PASSWORD_FILE}"
fi
chmod 600 "${APP_PASSWORD_FILE}"

# Umbrel expects `exports.sh` to output KEY=VALUE pairs; APP_PASSWORD is consumed
# for compose templating and login metadata display.
echo "APP_PASSWORD=${APP_PASSWORD}"
echo "APP_LNDG_PORT=8889"
