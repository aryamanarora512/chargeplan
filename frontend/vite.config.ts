import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// During development the browser talks to Vite (port 5173), and Vite forwards
// /api requests to the FastAPI server (port 8000). Same origin, so no CORS setup.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
