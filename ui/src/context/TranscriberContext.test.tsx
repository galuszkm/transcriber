import type { ReactNode } from "react";
import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  TranscriberProvider,
  useTranscriber,
} from "./TranscriberContext";

const wrapper = ({ children }: { children: ReactNode }) => (
  <TranscriberProvider>{children}</TranscriberProvider>
);

describe("TranscriberContext", () => {
  it("provides initial state", () => {
    const { result } = renderHook(() => useTranscriber(), { wrapper });

    expect(result.current.audioFile).toBeNull();
    expect(result.current.status).toBe("idle");
    expect(result.current.message).toBe("");
    expect(result.current.transcript).toBeNull();
    expect(result.current.view).toBe("segments");
    expect(result.current.diarize).toBe(false);
  });

  it("updates audioFile via setAudioFile", () => {
    const { result } = renderHook(() => useTranscriber(), { wrapper });

    const file = new File(["audio"], "test.wav", { type: "audio/wav" });
    act(() => result.current.setAudioFile(file));

    expect(result.current.audioFile).toBe(file);
  });

  it("reset clears state back to initial", () => {
    const { result } = renderHook(() => useTranscriber(), { wrapper });

    const file = new File(["audio"], "test.wav", { type: "audio/wav" });
    act(() => result.current.setAudioFile(file));
    act(() => result.current.reset());

    expect(result.current.audioFile).toBeNull();
    expect(result.current.status).toBe("idle");
    expect(result.current.message).toBe("");
    expect(result.current.transcript).toBeNull();
  });

  it("does nothing when submit is called without a file", () => {
    const { result } = renderHook(() => useTranscriber(), { wrapper });

    act(() => result.current.submit());

    expect(result.current.status).toBe("idle");
  });

  it("transitions to transcribing when submit is called with a file", async () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => { }));

    const { result } = renderHook(() => useTranscriber(), { wrapper });

    const file = new File(["audio"], "test.wav", { type: "audio/wav" });
    act(() => result.current.setAudioFile(file));
    act(() => result.current.submit());

    expect(result.current.status).toBe("transcribing");
    expect(result.current.message).toContain("Uploading…");

    vi.restoreAllMocks();
  });

  it("switches view via setView", () => {
    const { result } = renderHook(() => useTranscriber(), { wrapper });

    act(() => result.current.setView("script"));
    expect(result.current.view).toBe("script");

    act(() => result.current.setView("plain"));
    expect(result.current.view).toBe("plain");
  });

  it("throws when used outside provider", () => {
    expect(() => {
      renderHook(() => useTranscriber());
    }).toThrow("useTranscriber must be used inside <TranscriberProvider>");
  });
});
