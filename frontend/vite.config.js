import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const rootDir = path.resolve(__dirname, '..');
  const env = loadEnv(mode, rootDir, '');
  const apiTarget = (env.VITE_DEV_API_TARGET || env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

  return {
    plugins: [react()],
    envDir: rootDir,
    server: {
      host: '127.0.0.1',
      port: 3000,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/static': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/media': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
