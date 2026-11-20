import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Os artigos vivem em ../docs/research e sao importados como texto (?raw).
  server: { fs: { allow: ['..'] } },
});
