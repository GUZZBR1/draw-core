/**
 * Cliente do Draw na nuvem (preparado, desligado por padrao).
 *
 * Ativa so quando VITE_DRAW_CLOUD_URL existe (ex.: wss://draw.exemplo.com/live).
 * Sem a variavel, `isCloudConfigured()` e false e o estudio funciona como antes.
 *
 * Contrato (WebSocket):
 *   cliente -> servidor
 *     1) texto, ao abrir:  {"type":"hello","token":"<VITE_DRAW_CLOUD_TOKEN>","v":1}
 *     2) binario, ~4x/s:   um JPEG completo por mensagem (um quadro da camera)
 *   servidor -> cliente (texto, JSON)
 *     {"type":"ready"}                                  handshake aceito
 *     {"type":"result",
 *      "seq": number,                                   ordem crescente
 *      "quad": [[x,y],[x,y],[x,y],[x,y]] | null,        folha detectada, 0..1 sobre o quadro enviado
 *      "ink": "data:image/png;base64,..." | null,       tinta confirmada (PNG, fundo transparente)
 *      "hand": boolean | null}                          mao sobre a folha
 *     {"type":"error","message": string}
 *
 * O token vai na mensagem `hello` (nao na URL) para nao parar em log de proxy.
 */

export type CloudStatus = 'off' | 'connecting' | 'ready' | 'error';

export interface CloudResult {
  seq: number;
  quad: [number, number][] | null;
  ink: string | null;
  hand: boolean | null;
}

export interface CloudHandlers {
  onStatus: (status: CloudStatus, detail?: string) => void;
  onResult: (result: CloudResult) => void;
}

const URL_ENV = import.meta.env.VITE_DRAW_CLOUD_URL as string | undefined;
const TOKEN_ENV = import.meta.env.VITE_DRAW_CLOUD_TOKEN as string | undefined;

export const isCloudConfigured = () => Boolean(URL_ENV);

// Acima disso o quadro em voo fica velho: descarta em vez de enfileirar (latest-wins).
const MAX_BUFFERED_BYTES = 512 * 1024;

export class DrawCloud {
  private ws: WebSocket | null = null;
  private ready = false;
  private lastSeq = -1;
  private closed = false;

  constructor(private readonly handlers: CloudHandlers) {}

  connect() {
    if (!URL_ENV || this.ws) return;
    this.closed = false;
    this.handlers.onStatus('connecting');
    let ws: WebSocket;
    try {
      ws = new WebSocket(URL_ENV);
    } catch {
      this.handlers.onStatus('error', 'endereço inválido');
      return;
    }
    ws.binaryType = 'arraybuffer';
    this.ws = ws;
    ws.onopen = () => ws.send(JSON.stringify({ type: 'hello', token: TOKEN_ENV ?? '', v: 1 }));
    ws.onmessage = (ev) => {
      if (typeof ev.data !== 'string') return;
      let msg: { type?: string; message?: string } & Partial<CloudResult>;
      try { msg = JSON.parse(ev.data); } catch { return; }
      if (msg.type === 'ready') {
        this.ready = true;
        this.handlers.onStatus('ready');
      } else if (msg.type === 'result' && typeof msg.seq === 'number' && msg.seq > this.lastSeq) {
        this.lastSeq = msg.seq;
        this.handlers.onResult({ seq: msg.seq, quad: msg.quad ?? null, ink: msg.ink ?? null, hand: msg.hand ?? null });
      } else if (msg.type === 'error') {
        this.handlers.onStatus('error', msg.message);
      }
    };
    ws.onerror = () => { if (!this.closed) this.handlers.onStatus('error', 'sem conexão com o Draw'); };
    ws.onclose = () => {
      this.ws = null;
      this.ready = false;
      if (!this.closed) this.handlers.onStatus('error', 'conexão encerrada');
    };
  }

  /** Envia um quadro JPEG; devolve false se descartou (nao pronto ou fila cheia). */
  sendFrame(jpeg: Blob): boolean {
    const ws = this.ws;
    if (!ws || !this.ready || ws.readyState !== WebSocket.OPEN) return false;
    if (ws.bufferedAmount > MAX_BUFFERED_BYTES) return false;
    ws.send(jpeg);
    return true;
  }

  close() {
    this.closed = true;
    this.ws?.close();
    this.ws = null;
    this.ready = false;
    this.lastSeq = -1;
    this.handlers.onStatus('off');
  }
}
