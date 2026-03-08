import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("App", () => {
  it("renders the heading", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /transcriber/i })).toBeInTheDocument();
  });

  it("renders the upload area", () => {
    render(<App />);
    expect(screen.getByText(/click or drop an audio file here/i)).toBeInTheDocument();
  });

  it("renders the record button", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: /record/i })).toBeInTheDocument();
  });

  it("renders the transcribe button (disabled without file)", () => {
    render(<App />);
    const btn = screen.getByRole("button", { name: /transcribe/i });
    expect(btn).toBeInTheDocument();
    expect(btn).toBeDisabled();
  });
});
