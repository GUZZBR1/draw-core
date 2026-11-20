/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Endereco WebSocket do Draw na nuvem (wss://...). Sem ele, o recurso fica desligado. */
  readonly VITE_DRAW_CLOUD_URL?: string;
  readonly VITE_DRAW_CLOUD_TOKEN?: string;
}
