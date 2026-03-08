import type { TranscribeResponse } from "../types";

/** Resolve the API base URL from server config or relative path. */
function getApiBase(): string {
  return window.__SERVER_CONFIG__?.apiBaseUrl ?? ".";
}

/**
 * Upload an audio file to the transcription endpoint.
 * Returns the parsed transcription response.
 */
export async function transcribeFile(
  file: File,
  signal?: AbortSignal,
): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${getApiBase()}/transcribe`, {
    method: "POST",
    body: form,
    signal,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Server error: ${res.status}`);
  }

  return res.json() as Promise<TranscribeResponse>;
}
