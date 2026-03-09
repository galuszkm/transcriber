import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import TranscriptDisplay from "./TranscriptDisplay";
import { TranscriberProvider } from "../context/TranscriberContext";

describe("TranscriptDisplay", () => {
  it("renders nothing when there is no transcript", () => {
    const { container } = render(
      <TranscriberProvider>
        <TranscriptDisplay />
      </TranscriberProvider>,
    );
    expect(container.querySelector(".transcript-card")).toBeNull();
  });
});
