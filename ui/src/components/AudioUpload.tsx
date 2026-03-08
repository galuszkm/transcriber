import { useRef } from "react";
import { Button, Flex, Text, View } from "@aws-amplify/ui-react";
import { FiUploadCloud, FiFile } from "react-icons/fi";
import { useTranscriber } from "../context/TranscriberContext";

/** File types accepted by the audio upload input. */
const ACCEPTED = "audio/*,.wav,.mp3,.m4a,.ogg,.flac,.webm";

/**
 * Drag-and-drop or click-to-browse audio file upload area.
 *
 * Shows the selected filename when a file is loaded, or a prompt otherwise.
 * Disabled while a transcription is in progress.
 */
export default function AudioUpload() {
  const { audioFile, setAudioFile, status } = useTranscriber();
  const inputRef = useRef<HTMLInputElement>(null);
  const busy = status === "transcribing";

  /** Handle file selection from the native file picker. */
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setAudioFile(file);
  };

  /** Programmatically open the native file picker. */
  const openPicker = () => {
    if (!busy) inputRef.current?.click();
  };

  /** Accept a dropped audio file. */
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

  /** Render the inner content: icon + filename or prompt text. */
  function renderContent() {
    if (audioFile) {
      return (
        <>
          <FiFile size={24} />
          <Text fontWeight="bold" data-testid="file-name">
            {audioFile.name}
          </Text>
        </>
      );
    }
    return (
      <>
        <FiUploadCloud size={28} />
        <Text color="font.tertiary">Click or drag an audio file here</Text>
      </>
    );
  }

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
        {renderContent()}
        <Button size="small" variation="link" isDisabled={busy}>
          Browse files
        </Button>
      </Flex>
    </View>
  );
}
