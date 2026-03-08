import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import TranscriptSegments from "./TranscriptSegments";
import type { Segment } from "../types";

const segments: Segment[] = [
  { start: 0, end: 5, text: "Hello world", speaker: "Alice" },
  { start: 5, end: 10, text: "Goodbye", speaker: "Bob" },
];

describe("TranscriptSegments", () => {
  it("renders all segments", () => {
    render(<TranscriptSegments segments={segments} />);
    expect(screen.getByText("Hello world")).toBeInTheDocument();
    expect(screen.getByText("Goodbye")).toBeInTheDocument();
  });

  it("shows speaker names", () => {
    render(<TranscriptSegments segments={segments} />);
    expect(screen.getByText("Alice:")).toBeInTheDocument();
    expect(screen.getByText("Bob:")).toBeInTheDocument();
  });

  it("shows timestamps", () => {
    render(<TranscriptSegments segments={segments} />);
    expect(screen.getByText("[00:00-00:05]")).toBeInTheDocument();
  });
});
