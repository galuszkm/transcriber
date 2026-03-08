import { useRef } from "react";
import { Button, Flex, Text, View } from "@aws-amplify/ui-react";
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

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (busy) return;
    const file = e.dataTransfer.files[0] ?? null;
    if (file && file.type.startsWith("audio/")) {
      setAudioFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  return (
    <View
      className="upload-area"
      role="button"
      tabIndex={0}
      onClick={openPicker}
      onKeyDown={(e: React.KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") openPicker();
      }}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      aria-label="Upload audio file"
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        onChange={handleChange}
        disabled={busy}
        data-testid="file-input"
        style={{ display: "none" }}
      />
      <Flex direction="column" alignItems="center" gap="0.25rem">
        <Text fontSize="1.5rem">&#128190;</Text>
        {audioFile ? (
          <Text fontWeight="bold" data-testid="file-name">
            {audioFile.name}
          </Text>
        ) : (
          <Text color="font.tertiary">
            Click or drag an audio file here
          </Text>
        )}
        <Button size="small" variation="link" isDisabled={busy}>
          Browse files
        </Button>
      </Flex>
    </View>
  );
}
