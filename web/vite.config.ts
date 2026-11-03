import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // MapLibre 6 loads its web worker relative to its own module; pre-bundling breaks that URL.
  optimizeDeps: { exclude: ['maplibre-gl'] },
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
