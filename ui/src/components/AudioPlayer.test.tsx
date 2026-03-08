import { render } from "@testing-library/react";
import { describe, expect, it, vi, beforeAll, afterAll } from "vitest";
import AudioPlayer from "./AudioPlayer";
import { TranscriberProvider } from "../context/TranscriberContext";

// Mock URL.createObjectURL / revokeObjectURL for jsdom
beforeAll(() => {
  vi.stubGlobal("URL", {
    ...globalThis.URL,
    createObjectURL: vi.fn(() => "blob:mock-url"),
    revokeObjectURL: vi.fn(),
  });
});

afterAll(() => {
  vi.unstubAllGlobals();
});

describe("AudioPlayer", () => {
  it("renders nothing when there is no audio file or status is not done", () => {
    const { container } = render(
      <TranscriberProvider>
        <AudioPlayer />
      </TranscriberProvider>,
    );
    expect(container.querySelector(".audio-player-card")).toBeNull();
  });
});
