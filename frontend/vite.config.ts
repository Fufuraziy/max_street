import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// В dev-режиме запросы /api проксируются на локальный бэкенд, в Docker это делает Nginx.
export default defineConfig({
  base: '/max_street/',
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  preview: {
    port: 4173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1000,
  },
});
