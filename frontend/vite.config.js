import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// Vite config for LNDg SPA (6-F)
// Output goes to gui/static/spa/ so Django can serve the bundle via
// {% static 'spa/index.js' %} / {% static 'spa/index.css' %}
export default defineConfig({
  plugins: [react()],
  root: '.',
  base: '/static/spa/',
  build: {
    outDir: resolve(__dirname, '../gui/static/spa'),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(__dirname, 'index.html'),
      output: {
        entryFileNames: 'index.js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) return 'index.css'
          return 'assets/[name]-[hash][extname]'
        },
      },
    },
  },
  server: {
    // Dev server proxies API calls to Django (default port 8000)
    proxy: {
      '/api': 'http://localhost:8000',
      '/lndg-admin': 'http://localhost:8000',
    },
  },
})
