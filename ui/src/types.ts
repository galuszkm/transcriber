/** A single transcript segment returned by the server. */
export interface Segment {
  start: number;
  end: number;
  text: string;
  speaker?: string;
}

/** Full transcription response from the server. */
export interface TranscribeResponse {
  segments: Segment[];
  language: string;
  duration: number;
  timings?: Record<string, number>;
}
