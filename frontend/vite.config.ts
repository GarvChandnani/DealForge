import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env from the frontend directory (default behaviour)
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    server: {
      port: 5173,
      proxy: {
        // Dev proxy: forward /api/* requests to the FastAPI backend
        // In production, VITE_API_URL is used directly by the Axios client —
        // no proxy is needed because the browser calls the backend URL directly.
        '/api': {
          target: env.VITE_API_URL ?? 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      // Emit source maps for easier debugging in production
      sourcemap: false,
      // Output to dist/ (default — aligns with render.yaml staticPublishPath)
      outDir: 'dist',
    },
  }
})
