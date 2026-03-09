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

/** SSE progress event payload (`event: progress`). */
export interface SSEProgressEvent {
  stage: string;
  message: string;
}

/** SSE complete event payload (`event: complete`) — same shape as TranscribeResponse. */
export type SSECompleteEvent = TranscribeResponse;

/** SSE error event payload (`event: error`). */
export interface SSEErrorEvent {
  detail: string;
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

/** Callbacks for `transcribeFileSSE`. */
export interface SSECallbacks {
  onProgress: (stage: string, message: string) => void;
  onComplete: (result: TranscribeResponse) => void;
  onError: (err: Error) => void;
  signal?: AbortSignal;
}

/** Possible status values for the transcription workflow. */
export type Status = "idle" | "transcribing" | "done" | "error";

/** Which transcript view tab is active. */
export type TranscriptView = "segments" | "script" | "plain";

/** User-controlled settings persisted to localStorage. */
export interface PersistedSettings {
  diarize: boolean;
  autoCopy: boolean;
  transcriptCollapsed: boolean;
  showDropzone: boolean;
  darkMode: boolean;
}

/** Shape of the transcriber context consumed by child components. */
export interface TranscriberState {
  // transient state
  audioFile: File | null;
  status: Status;
  stage: string;
  message: string;
  transcript: TranscribeResponse | null;
  view: TranscriptView;
  isRecording: boolean;

  // persisted settings
  diarize: boolean;
  autoCopy: boolean;
  transcriptCollapsed: boolean;
  showDropzone: boolean;
  darkMode: boolean;

  // actions
  setAudioFile: (file: File | null) => void;
  setDiarize: (enabled: boolean) => void;
  setAutoCopy: (enabled: boolean) => void;
  setIsRecording: (recording: boolean) => void;
  setTranscriptCollapsed: (collapsed: boolean) => void;
  setShowDropzone: (show: boolean) => void;
  setDarkMode: (dark: boolean) => void;
  submit: () => void;
  cancel: () => void;
  reset: () => void;
  setView: (view: TranscriptView) => void;
}
