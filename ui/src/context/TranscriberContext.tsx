/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { TranscribeResponse } from "../types";
import { transcribeFile } from "../api/transcribe";

/** Possible status values for the transcription workflow. */
export type Status = "idle" | "transcribing" | "done" | "error";

/** Which transcript view is active. */
export type TranscriptView = "segments" | "script" | "plain";

interface TranscriberState {
  audioFile: File | null;
  status: Status;
  message: string;
  transcript: TranscribeResponse | null;
  view: TranscriptView;

  setAudioFile: (file: File | null) => void;
  submit: () => void;
  cancel: () => void;
  reset: () => void;
  setView: (view: TranscriptView) => void;
}

const TranscriberContext = createContext<TranscriberState | null>(null);

export function TranscriberProvider({ children }: { children: ReactNode }) {
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [transcript, setTranscript] = useState<TranscribeResponse | null>(null);
  const [view, setView] = useState<TranscriptView>("segments");
  const abortRef = useRef<AbortController | null>(null);

  const submit = useCallback(() => {
    if (!audioFile) return;

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setStatus("transcribing");
    setMessage("Uploading and transcribing...");
    setTranscript(null);

    transcribeFile(audioFile, ctrl.signal)
      .then((result) => {
        setTranscript(result);
        setStatus("done");
        setMessage("Transcription complete.");
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") {
          setStatus("idle");
          setMessage("Cancelled.");
          return;
        }
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Unknown error");
      });
  }, [audioFile]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const reset = useCallback(() => {
    cancel();
    setAudioFile(null);
    setStatus("idle");
    setMessage("");
    setTranscript(null);
  }, [cancel]);

  return (
    <TranscriberContext.Provider
      value={{
        audioFile,
        status,
        message,
        transcript,
        view,
        setAudioFile,
        submit,
        cancel,
        reset,
        setView,
      }}
    >
      {children}
    </TranscriberContext.Provider>
  );
}

/** Consume the transcriber context; throws if used outside provider. */
export function useTranscriber(): TranscriberState {
  const ctx = useContext(TranscriberContext);
  if (!ctx) {
    throw new Error("useTranscriber must be used inside <TranscriberProvider>");
  }
  return ctx;
}
