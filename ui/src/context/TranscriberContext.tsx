/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { TranscribeResponse, PersistedSettings, Status, TranscriptView, TranscriberState } from "../types";
import { transcribeFileSSE } from "../api/transcribe";
import { copyToClipboard, toPlainText } from "../utils/format";

// ---------------------------------------------------------------------------
// Persisted settings
// ---------------------------------------------------------------------------

const SETTINGS_KEY = "transcriber-settings";

const SETTINGS_DEFAULTS: PersistedSettings = {
  diarize: false,
  autoCopy: false,
  transcriptCollapsed: false,
  showDropzone: true,
  darkMode: false,
};

function loadSettings(): PersistedSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (raw) return { ...SETTINGS_DEFAULTS, ...(JSON.parse(raw) as Partial<PersistedSettings>) };
  } catch {
    // ignore corrupt data
  }
  return SETTINGS_DEFAULTS;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const TranscriberContext = createContext<TranscriberState | null>(null);

/**
 * Provides transcription state and actions to the component tree.
 *
 * Wraps the entire app so any child can call `useTranscriber()` to access
 * audio file, transcription status, results, and control actions.
 */
export const TranscriberProvider = ({ children }: { children: ReactNode }) => {
  // transient state
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [stage, setStage] = useState("");
  const [message, setMessage] = useState("");
  const [transcript, setTranscript] = useState<TranscribeResponse | null>(null);
  const [view, setView] = useState<TranscriptView>("segments");
  const [isRecording, setIsRecording] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // persisted settings — initialised from localStorage once
  const _s = loadSettings();
  const [diarize, setDiarize] = useState(_s.diarize);
  const [autoCopy, setAutoCopy] = useState(_s.autoCopy);
  const [transcriptCollapsed, setTranscriptCollapsed] = useState(_s.transcriptCollapsed);
  const [showDropzone, setShowDropzone] = useState(_s.showDropzone);
  const [darkMode, setDarkMode] = useState(_s.darkMode);

  // persist settings whenever any of them change
  useEffect(() => {
    localStorage.setItem(
      SETTINGS_KEY,
      JSON.stringify({ diarize, autoCopy, transcriptCollapsed, showDropzone, darkMode }),
    );
  }, [diarize, autoCopy, transcriptCollapsed, showDropzone, darkMode]);

  /** Upload the audio file and start transcription via SSE streaming. */
  const submit = useCallback(() => {
    if (!audioFile) return;

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setStatus("transcribing");
    setStage("");
    setMessage("Uploading…");
    setTranscript(null);

    transcribeFileSSE(audioFile, diarize, {
      signal: ctrl.signal,
      onProgress: (s, msg) => {
        setStage(s);
        setMessage(msg);
      },
      onComplete: (result) => {
        setTranscript(result);
        setStage("");
        setStatus("done");
        setMessage("Transcription complete.");
        if (autoCopy) copyToClipboard(toPlainText(result));
      },
      onError: (err) => {
        if (err instanceof DOMException && err.name === "AbortError") {
          setStage("");
          setStatus("idle");
          setMessage("Cancelled.");
          return;
        }
        setStage("");
        setStatus("error");
        setMessage(err.message || "Unknown error");
      },
    });
  }, [audioFile, diarize, autoCopy]);

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
    setStage("");
    setMessage("");
    setTranscript(null);
  }, [cancel]);

  return (
    <TranscriberContext.Provider
      value={{
        audioFile,
        status,
        stage,
        message,
        transcript,
        view,
        isRecording,
        diarize,
        autoCopy,
        transcriptCollapsed,
        showDropzone,
        darkMode,
        setAudioFile,
        setDiarize,
        setAutoCopy,
        setIsRecording,
        setTranscriptCollapsed,
        setShowDropzone,
        setDarkMode,
        submit,
        cancel,
        reset,
        setView,
      }}
    >
      {children}
    </TranscriberContext.Provider>
  );
};

/**
 * Consume the transcriber context.
 *
 * @throws Error if called outside of `<TranscriberProvider>`.
 */
export const useTranscriber = (): TranscriberState => {
  const ctx = useContext(TranscriberContext);
  if (!ctx) {
    throw new Error("useTranscriber must be used inside <TranscriberProvider>");
  }
  return ctx;
};
