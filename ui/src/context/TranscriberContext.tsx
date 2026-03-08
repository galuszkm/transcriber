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

/** Which transcript view tab is active. */
export type TranscriptView = "segments" | "script" | "plain";

/** Shape of the transcriber context consumed by child components. */
interface TranscriberState {
  audioFile: File | null;
  status: Status;
  message: string;
  transcript: TranscribeResponse | null;
  view: TranscriptView;
  diarize: boolean;

  setAudioFile: (file: File | null) => void;
  setDiarize: (enabled: boolean) => void;
  submit: () => void;
  cancel: () => void;
  reset: () => void;
  setView: (view: TranscriptView) => void;
}

const TranscriberContext = createContext<TranscriberState | null>(null);

/**
 * Provides transcription state and actions to the component tree.
 *
 * Wraps the entire app so any child can call `useTranscriber()` to access
 * audio file, transcription status, results, and control actions.
 */
export function TranscriberProvider({ children }: { children: ReactNode }) {
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [transcript, setTranscript] = useState<TranscribeResponse | null>(null);
  const [view, setView] = useState<TranscriptView>("segments");
  const [diarize, setDiarize] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  /** Upload the audio file and start transcription. */
  const submit = useCallback(() => {
    if (!audioFile) return;

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setStatus("transcribing");
    setMessage("Uploading and transcribing...");
    setTranscript(null);

    transcribeFile(audioFile, { signal: ctrl.signal, diarize })
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
  }, [audioFile, diarize]);

  /** Abort an in-progress transcription request. */
  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  /** Reset all state back to initial (idle, no file, no transcript). */
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
        diarize,
        setAudioFile,
        setDiarize,
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

/**
 * Consume the transcriber context.
 *
 * @throws Error if called outside of `<TranscriberProvider>`.
 */
export function useTranscriber(): TranscriberState {
  const ctx = useContext(TranscriberContext);
  if (!ctx) {
    throw new Error("useTranscriber must be used inside <TranscriberProvider>");
  }
  return ctx;
}

