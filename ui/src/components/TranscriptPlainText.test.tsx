import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import TranscriptPlainText from "./TranscriptPlainText";

describe("TranscriptPlainText", () => {
  it("renders the transcript text in a textarea", () => {
    render(<TranscriptPlainText text="Hello world transcript" />);
    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveValue("Hello world transcript");
  });

  it("is read-only", () => {
    render(<TranscriptPlainText text="test" />);
    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveAttribute("readonly");
  });
});
