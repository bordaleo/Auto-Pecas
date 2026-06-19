import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { createProxyMiddleware } from 'http-proxy-middleware';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;
const API_TARGET = process.env.API_URL || 'http://127.0.0.1:8000';
const frontendDist = path.join(__dirname, '..', 'frontend', 'dist');

const app = express();

app.use('/api', createProxyMiddleware({
  target: API_TARGET,
  changeOrigin: true,
}));

app.use('/static', createProxyMiddleware({
  target: API_TARGET,
  changeOrigin: true,
}));

app.use('/media', createProxyMiddleware({
  target: API_TARGET,
  changeOrigin: true,
}));

app.use(express.static(frontendDist));

app.get('*', (_req, res) => {
  res.sendFile(path.join(frontendDist, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Galelugi Peças — frontend em http://127.0.0.1:${PORT}`);
  console.log(`API proxy → ${API_TARGET}`);
});
