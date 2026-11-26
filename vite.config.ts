import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.API_PROXY ?? 'http://127.0.0.1:8000',
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/frontend/**/*.test.{ts,tsx}'],
    restoreMocks: true,
    setupFiles: ['./tests/frontend/setup.ts'],
  },
});
