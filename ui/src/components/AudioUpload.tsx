import { useRef } from "react";
import { useTranscriber } from "../context/TranscriberContext";

const ACCEPTED = "audio/*,.wav,.mp3,.m4a,.ogg,.flac,.webm";

export default function AudioUpload() {
  const { audioFile, setAudioFile, status } = useTranscriber();
  const inputRef = useRef<HTMLInputElement>(null);
  const busy = status === "transcribing";

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setAudioFile(file);
  };

  const openPicker = () => {
    if (!busy) inputRef.current?.click();
  };

  return (
    <div
      className="upload-area"
      role="button"
      tabIndex={0}
      onClick={openPicker}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") openPicker();
      }}
      aria-label="Upload audio file"
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        onChange={handleChange}
        disabled={busy}
        data-testid="file-input"
      />
      {audioFile ? (
        <p className="file-name">{audioFile.name}</p>
      ) : (
        <p>Click or drop an audio file here</p>
      )}
    </div>
  );
}
