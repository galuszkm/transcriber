import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Flex, Text, Badge } from "@aws-amplify/ui-react";
import { FiMic, FiSquare } from "react-icons/fi";
import { useTranscriber } from "../context/TranscriberContext";
import { formatTime } from "../utils/format";

/** Maximum recording duration in seconds. */
const MAX_SECONDS = 300; // 5 minutes

export default function AudioRecorder() {
  const { setAudioFile, status } = useTranscriber();
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const busy = status === "transcribing";

  const stopRecording = useCallback(() => {
    recorderRef.current?.stop();
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    setRecording(false);
    setElapsed(0);
  }, []);

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

      let ticks = 0;
      const id = setInterval(() => {
        ticks += 1;
        if (ticks >= MAX_SECONDS) {
          recorder.stop();
          clearInterval(id);
          timerRef.current = null;
          setRecording(false);
          setElapsed(0);
          return;
        }
        setElapsed(ticks);
      }, 1000);
      timerRef.current = id;
    } catch {
      // Mic permission denied or unavailable
    }
  }, [setAudioFile]);

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      recorderRef.current?.stream.getTracks().forEach((t) => t.stop());
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  if (recording) {
    return (
      <Flex alignItems="center" gap="0.75rem">
        <Badge variation="error" className="recording-badge">
          &#9679; REC
        </Badge>
        <Text fontFamily="monospace" fontSize="0.875rem" data-testid="timer">
          {formatTime(elapsed)} / {formatTime(MAX_SECONDS)}
        </Text>
        <Button variation="destructive" size="small" onClick={stopRecording} className="btn-icon">
          <FiSquare size={14} />
          Stop
        </Button>
      </Flex>
    );
  }

  return (
    <Button size="small" onClick={startRecording} isDisabled={busy} className="btn-icon">
      <FiMic size={14} />
      Record
    </Button>
  );
}
