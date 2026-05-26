import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // Path aliases — import from '@/components/...' instead of '../../'
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  // Proxy API calls to the Django dev server during development.
  // In production, Nginx / reverse-proxy handles this.
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target:       'http://localhost:8000',
        changeOrigin: true,
        secure:       false,
      },
      '/t': {                  // tracking pixel / click redirect
        target:       'http://localhost:8000',
        changeOrigin: true,
        secure:       false,
      },
    },
  },

  build: {
    outDir:           '../staticfiles/frontend',  // serve via Django whitenoise
    emptyOutDir:      true,
    sourcemap:        false,
    rollupOptions: {
      output: {
        // Split vendor chunks for better caching
        manualChunks: {
          vendor:   ['react', 'react-dom', 'react-router-dom'],
          charts:   ['recharts'],
          forms:    ['react-hook-form', 'zod', '@hookform/resolvers'],
        },
      },
    },
  },
});