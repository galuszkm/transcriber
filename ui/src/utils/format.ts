import type { TranscribeResponse, Segment } from "../types";

/**
 * Format seconds as `MM:SS` for display.
 *
 * @param sec - Duration in seconds.
 * @returns Formatted time string, e.g. `"03:45"`.
 */
export function formatTime(sec: number): string {
  const abs = Math.max(0, sec);
  const m = Math.floor(abs / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(abs % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

/**
 * Extract the plain-text transcript from the response.
 *
 * @param res - Full transcription response.
 * @returns The plain transcript string.
 */
export function toPlainText(res: TranscribeResponse): string {
  return res.transcript;
}

/**
 * Build a movie-script-style transcript grouped by speaker.
 *
 * Adjacent segments from the same speaker are merged under a single
 * uppercase speaker heading, producing output like:
 * ```
 * SPEAKER_00
 * Hello, how are you?
 *
 * SPEAKER_01
 * I'm good, thanks.
 * ```
 *
 * @param res - Full transcription response.
 * @returns The formatted script string.
 */
export function toScript(res: TranscribeResponse): string {
  const lines: string[] = [];
  let lastSpeaker = "";

  for (const seg of res.segments) {
    const speaker = seg.speaker ?? "Speaker";
    if (speaker !== lastSpeaker) {
      if (lines.length > 0) lines.push("");
      lines.push(speaker.toUpperCase());
      lastSpeaker = speaker;
    }
    lines.push(seg.text.trim());
  }

  return lines.join("\n");
}

/**
 * Build a markdown-formatted transcript with timestamps and optional speakers.
 *
 * @param res - Full transcription response.
 * @returns Markdown string ready for copy or download.
 */
export function toMarkdown(res: TranscribeResponse): string {
  const lines: string[] = [
    `# Transcript`,
    "",
    `**Language:** ${res.language} | **Duration:** ${formatTime(res.duration)}`,
    "",
  ];

  const hasSpeakers = res.segments.some((s) => s.speaker);

  if (hasSpeakers) {
    let lastSpeaker = "";
    for (const seg of res.segments) {
      const speaker = seg.speaker ?? "Speaker";
      if (speaker !== lastSpeaker) {
        lines.push("");
        lines.push(`### ${speaker}`);
        lines.push("");
        lastSpeaker = speaker;
      }
      lines.push(
        `\`[${formatTime(seg.start)}-${formatTime(seg.end)}]\` ${seg.text.trim()}`,
      );
    }
  } else {
    for (const seg of res.segments) {
      lines.push(
        `\`[${formatTime(seg.start)}-${formatTime(seg.end)}]\` ${seg.text.trim()}`,
      );
    }
  }

  return lines.join("\n");
}

/**
 * Serialize segments to a pretty-printed JSON string.
 *
 * @param segments - Array of transcript segments.
 * @returns Indented JSON string.
 */
export function toSegmentsJson(segments: Segment[]): string {
  return JSON.stringify(segments, null, 2);
}

/**
 * Serialize the full transcription response to a pretty-printed JSON string.
 *
 * @param res - Full transcription response.
 * @returns Indented JSON string.
 */
export function toFullJson(res: TranscribeResponse): string {
  return JSON.stringify(res, null, 2);
}

/**
 * Trigger a file download in the browser from a string content.
 *
 * Creates a temporary Blob URL, clicks a hidden `<a>` element, then revokes.
 *
 * @param content - The file content as a string.
 * @param filename - Suggested download filename.
 * @param mime - MIME type for the blob (default: `text/plain`).
 */
export function downloadFile(
  content: string,
  filename: string,
  mime = "text/plain",
): void {
  const blob = new Blob([content], { type: mime });
  downloadBlob(blob, filename);
}

/**
 * Trigger a file download in the browser from a Blob or File.
 *
 * @param blob - The Blob or File to download.
 * @param filename - Suggested download filename.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Copy text to the clipboard.
 *
 * @param text - The string to copy.
 * @returns `true` if the copy succeeded, `false` otherwise.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
