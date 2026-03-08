import { describe, expect, it } from "vitest";
import { formatTime, toPlainText, toScript, toMarkdown, toSegmentsJson, toFullJson } from "./format";
import type { TranscribeResponse } from "../types";

const response: TranscribeResponse = {
  transcript: "Hello world. Goodbye.",
  segments: [
    { start: 0, end: 5, text: "Hello world.", speaker: "Alice" },
    { start: 5, end: 8, text: "Goodbye.", speaker: "Bob" },
  ],
  language: "en",
  duration: 8,
};

const noSpeakerResponse: TranscribeResponse = {
  transcript: "Just some text.",
  segments: [
    { start: 0, end: 5, text: "Just some text." },
  ],
  language: "en",
  duration: 5,
};

describe("formatTime", () => {
  it("formats zero seconds", () => {
    expect(formatTime(0)).toBe("00:00");
  });

  it("formats minutes and seconds", () => {
    expect(formatTime(65)).toBe("01:05");
  });

  it("formats large values", () => {
    expect(formatTime(3661)).toBe("61:01");
  });
});

describe("toPlainText", () => {
  it("returns the transcript field", () => {
    expect(toPlainText(response)).toBe("Hello world. Goodbye.");
  });
});

describe("toScript", () => {
  it("groups by speaker in uppercase", () => {
    const result = toScript(response);
    expect(result).toContain("ALICE");
    expect(result).toContain("BOB");
    expect(result).toContain("Hello world.");
  });
});

describe("toMarkdown", () => {
  it("includes header and language", () => {
    const md = toMarkdown(response);
    expect(md).toContain("# Transcript");
    expect(md).toContain("**Language:** en");
  });

  it("includes speaker headings for diarized", () => {
    const md = toMarkdown(response);
    expect(md).toContain("### Alice");
    expect(md).toContain("### Bob");
  });

  it("omits speaker headings when no speakers", () => {
    const md = toMarkdown(noSpeakerResponse);
    expect(md).not.toContain("###");
  });
});

describe("toSegmentsJson", () => {
  it("returns valid JSON array", () => {
    const json = toSegmentsJson(response.segments);
    const parsed = JSON.parse(json);
    expect(parsed).toHaveLength(2);
    expect(parsed[0].text).toBe("Hello world.");
  });
});

describe("toFullJson", () => {
  it("returns valid JSON with all fields", () => {
    const json = toFullJson(response);
    const parsed = JSON.parse(json);
    expect(parsed.transcript).toBe("Hello world. Goodbye.");
    expect(parsed.segments).toHaveLength(2);
  });
});
