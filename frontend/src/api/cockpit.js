/**
 * API helpers for the LNDg SPA (6-F).
 *
 * CSRF token is read from the meta tag injected by the Django home view:
 *   <meta name="csrf-token" content="{{ csrf_token }}">
 */

function getCsrf() {
  const meta = document.querySelector('meta[name="csrf-token"]')
  return meta ? meta.getAttribute('content') : ''
}

async function apiFetch(path, options = {}) {
  const headers = {
    Accept: 'application/json',
    'X-CSRFToken': getCsrf(),
    ...options.headers,
  }
  const resp = await fetch(path, { ...options, headers })
  if (!resp.ok) throw new Error(`API ${path} → ${resp.status}`)
  return resp.json()
}

export async function fetchCockpit() {
  return apiFetch('/api/v2/cockpit/')
}

export async function fetchNetworkPeers(limit = 50) {
  return apiFetch(`/api/v2/network/peers/?limit=${limit}`)
}
