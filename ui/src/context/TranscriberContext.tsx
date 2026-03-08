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

interface TranscriberState {
  /** The audio file selected or recorded by the user. */
  audioFile: File | null;
  /** Current workflow status. */
  status: Status;
  /** Human‑readable progress / status message. */
  message: string;
  /** Transcription result, when status is "done". */
  transcript: TranscribeResponse | null;

  /** Set audio file (from upload or recording). */
  setAudioFile: (file: File | null) => void;
  /** Submit the current audio file for transcription. */
  submit: () => void;
  /** Cancel an in-flight transcription request. */
  cancel: () => void;
  /** Reset everything back to idle. */
  reset: () => void;
}

const TranscriberContext = createContext<TranscriberState | null>(null);

export function TranscriberProvider({ children }: { children: ReactNode }) {
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [transcript, setTranscript] = useState<TranscribeResponse | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const submit = useCallback(() => {
    if (!audioFile) return;

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setStatus("transcribing");
    setMessage("Uploading and transcribing…");
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
        setAudioFile,
        submit,
        cancel,
        reset,
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
