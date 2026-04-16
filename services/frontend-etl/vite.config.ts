import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'
import { defineConfig, loadEnv } from 'vite'

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load root-level .env.{mode} and merge into process.env so Vite exposes
  // them via import.meta.env.VITE_* in all component code
  const env = loadEnv(mode, resolve(__dirname, '../../'), '')
  Object.assign(process.env, env)

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
      },
    },
    server: {
      host: true, // Required for Docker
      port: 3333,
      strictPort: true, // Fail if port is already in use instead of auto-incrementing
      watch: {
        usePolling: true,
      },
      // Using direct axios calls with CORS
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom'],
            router: ['react-router-dom'],
            ui: ['framer-motion', 'lucide-react'],
          },
        },
      },
    },
  }
})
