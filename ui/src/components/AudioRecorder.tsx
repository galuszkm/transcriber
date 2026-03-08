import { useCallback, useEffect, useRef, useState } from "react";
import { useTranscriber } from "../context/TranscriberContext";

/** Maximum recording duration in seconds. */
const MAX_SECONDS = 300; // 5 minutes

/** Format seconds as mm:ss. */
function formatTime(sec: number): string {
  const m = Math.floor(sec / 60)
    .toString()
    .padStart(2, "0");
  const s = (sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function AudioRecorder() {
  const { setAudioFile, status } = useTranscriber();
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const busy = status === "transcribing";

  /** Stop recording, build a File from chunks, and pass it up. */
  const stopRecording = useCallback(() => {
    recorderRef.current?.stop();
    if (timerRef.current) clearInterval(timerRef.current);
    setRecording(false);
    setElapsed(0);
  }, []);

  /** Start capturing audio from the microphone. */
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const file = new File([blob], "recording.webm", { type: "audio/webm" });
        setAudioFile(file);
      };

      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
      setElapsed(0);

      const id = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
      timerRef.current = id;
    } catch {
      // Mic permission denied or unavailable – fail silently.
    }
  }, [setAudioFile]);

  // Auto-stop at MAX_SECONDS.
  useEffect(() => {
    if (recording && elapsed >= MAX_SECONDS) {
      stopRecording();
    }
  }, [recording, elapsed, stopRecording]);

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      recorderRef.current?.stream.getTracks().forEach((t) => t.stop());
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  if (recording) {
    return (
      <div className="recorder">
        <span className="recording-dot" />
        <span className="timer" data-testid="timer">
          {formatTime(elapsed)} / {formatTime(MAX_SECONDS)}
        </span>
        <button className="btn btn-danger" onClick={stopRecording} type="button">
          Stop
        </button>
      </div>
    );
  }

  return (
    <button
      className="btn"
      onClick={startRecording}
      disabled={busy}
      type="button"
    >
      Record
    </button>
  );
}
