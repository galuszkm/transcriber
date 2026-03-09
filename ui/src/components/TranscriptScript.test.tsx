import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import TranscriptScript from "./TranscriptScript";
import type { Segment } from "../types";

const segments: Segment[] = [
  { start: 0, end: 5, text: "Hello world", speaker: "Alice" },
  { start: 5, end: 8, text: "How are you?", speaker: "Alice" },
  { start: 8, end: 12, text: "I am fine", speaker: "Bob" },
];

describe("TranscriptScript", () => {
  it("groups consecutive segments by speaker", () => {
    render(<TranscriptScript segments={segments} />);
    const speakers = screen.getAllByRole("heading", { level: 5 });
    expect(speakers).toHaveLength(2);
    expect(speakers[0]).toHaveTextContent("Alice");
    expect(speakers[1]).toHaveTextContent("Bob");
  });

  it("joins text for same speaker", () => {
    render(<TranscriptScript segments={segments} />);
    expect(screen.getByText("Hello world How are you?")).toBeInTheDocument();
  });
});
