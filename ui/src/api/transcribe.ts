import type { TranscribeResponse } from "../types";

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

  const res = await fetch("./transcribe", {
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
