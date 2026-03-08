/** A single transcript segment returned by the server. */
export interface Segment {
  start: number;
  end: number;
  text: string;
  speaker?: string;
}

/** Full transcription response from the server. */
export interface TranscribeResponse {
  transcript: string;
  segments: Segment[];
  language: string;
  duration: number;
  timings?: Record<string, number>;
}

/** Server-injected configuration available on window.__SERVER_CONFIG__. */
export interface ServerConfig {
  apiBaseUrl: string;
  staticUrl: string;
}

declare global {
  interface Window {
    __SERVER_CONFIG__?: ServerConfig;
  }
}
