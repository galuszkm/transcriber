import type { SSEProgressEvent, SSECompleteEvent, SSEErrorEvent, SSECallbacks } from "../types";

/** Resolve the API base URL from server-injected config or fall back to ".". */
const getApiBase = (): string => window.__SERVER_CONFIG__?.apiBaseUrl ?? ".";

/**
 * Upload an audio file to the SSE streaming transcription endpoint.
 *
 * Fires `onProgress` for each pipeline stage update, `onComplete` with the
 * final result, or `onError` if the request fails or is aborted.
 *
 * @param file - The audio file to transcribe.
 * @param diarize - Whether to run speaker diarization.
 * @param callbacks - Event callbacks and optional abort signal.
 */
export const transcribeFileSSE = async (
  file: File,
  diarize: boolean,
  { onProgress, onComplete, onError, signal }: SSECallbacks,
): Promise<void> => {
  const form = new FormData();
  form.append("file", file);

  const qs = diarize ? "?diarize=true" : "";
  const url = `${getApiBase()}/transcribe/stream${qs}`;

  let res: Response;
  try {
    res = await fetch(url, { method: "POST", body: form, signal });
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)));
    return;
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    onError(new Error(text || `Server error: ${res.status}`));
    return;
  }

  if (!res.body) {
    onError(new Error("No response body from server"));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const processEvent = (block: string) => {
    let eventType = "";
    let dataLine = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) eventType = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLine = line.slice(5).trim();
    }
    if (!eventType || !dataLine) return;

    if (eventType === "progress") {
      const ev = JSON.parse(dataLine) as SSEProgressEvent;
      onProgress(ev.stage, ev.message);
    } else if (eventType === "complete") {
      const ev = JSON.parse(dataLine) as SSECompleteEvent;
      onComplete(ev);
    } else if (eventType === "error") {
      const ev = JSON.parse(dataLine) as SSEErrorEvent;
      onError(new Error(ev.detail));
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const block of events) {
        if (block.trim()) processEvent(block);
      }
    }
    // Flush any remaining buffer content
    if (buffer.trim()) processEvent(buffer);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      onError(err);
    } else {
      onError(err instanceof Error ? err : new Error(String(err)));
    }
  } finally {
    reader.releaseLock();
  }
};
