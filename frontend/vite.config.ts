import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Dev mode: the FastAPI backend runs separately on :8000.
      '/api': 'http://localhost:8000',
    },
  },
});
