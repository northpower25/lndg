import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './i18n.js'
import App from './App.jsx'

const rootEl = document.getElementById('lndg-root')
if (rootEl) {
  createRoot(rootEl).render(
    <StrictMode>
      <App />
    </StrictMode>
  )
}
