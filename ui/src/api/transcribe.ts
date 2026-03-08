import type { TranscribeResponse } from "../types";

/** Resolve the API base URL from server-injected config or fall back to ".". */
function getApiBase(): string {
  return window.__SERVER_CONFIG__?.apiBaseUrl ?? ".";
}

/** Options for the transcription request. */
interface TranscribeOptions {
  /** AbortSignal for cancellation. */
  signal?: AbortSignal;
  /** Whether to run speaker diarization. */
  diarize?: boolean;
}

/**
 * Upload an audio file to the transcription endpoint.
 *
 * @param file - The audio file to transcribe.
 * @param options - Optional signal for cancellation and diarization flag.
 * @returns The parsed transcription response from the server.
 */
export async function transcribeFile(
  file: File,
  options: TranscribeOptions = {},
): Promise<TranscribeResponse> {
  const { signal, diarize = false } = options;
  const form = new FormData();
  form.append("file", file);

  const params = new URLSearchParams();
  if (diarize) params.set("diarize", "true");

  const qs = params.toString();
  const url = `${getApiBase()}/transcribe${qs ? `?${qs}` : ""}`;

  const res = await fetch(url, { method: "POST", body: form, signal });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Server error: ${res.status}`);
  }

  return res.json() as Promise<TranscribeResponse>;
}
