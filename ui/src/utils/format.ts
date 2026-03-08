import type { TranscribeResponse, Segment } from "../types";

/** Format seconds to mm:ss display. */
export function formatTime(sec: number): string {
  const m = Math.floor(sec / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(sec % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

/** Build a plain-text transcript from the response. */
export function toPlainText(res: TranscribeResponse): string {
  return res.transcript;
}

/** Build a movie-script-style transcript (grouped by speaker). */
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

/** Build a markdown-formatted transcript with timestamps. */
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

/** Build a JSON string of the segments. */
export function toSegmentsJson(segments: Segment[]): string {
  return JSON.stringify(segments, null, 2);
}

/** Build a JSON string of the full response. */
export function toFullJson(res: TranscribeResponse): string {
  return JSON.stringify(res, null, 2);
}

/** Trigger a file download in the browser. */
export function downloadFile(
  content: string,
  filename: string,
  mime = "text/plain",
): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Copy text to clipboard. Returns true on success. */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
