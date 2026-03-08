import { useRef, useState } from "react";
import { Alert, Button, Flex, Text, View } from "@aws-amplify/ui-react";
import { FiUploadCloud, FiFile } from "react-icons/fi";
import { useTranscriber } from "../context/TranscriberContext";

const ACCEPTED = "audio/*,.wav,.mp3,.m4a,.ogg,.flac,.webm";
const MAX_BYTES = 50 * 1024 * 1024; // 50 MB

export default function AudioUpload() {
  const { audioFile, setAudioFile, status } = useTranscriber();
  const inputRef = useRef<HTMLInputElement>(null);
  const [sizeError, setSizeError] = useState(false);
  const busy = status === "transcribing";

  const trySetFile = (file: File | null) => {
    if (file && file.size > MAX_BYTES) {
      setSizeError(true);
      return;
    }
    setSizeError(false);
    setAudioFile(file);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    trySetFile(e.target.files?.[0] ?? null);
  };

  const openPicker = () => {
    if (!busy) inputRef.current?.click();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (busy) return;
    const file = e.dataTransfer.files[0] ?? null;
    if (file && file.type.startsWith("audio/")) trySetFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => e.preventDefault();

  return (
    <Flex direction="column" gap="0.5rem">
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
          {audioFile ? (
            <>
              <FiFile size={24} />
              <Text fontWeight="bold" data-testid="file-name">
                {audioFile.name}
              </Text>
            </>
          ) : (
            <>
              <FiUploadCloud size={28} />
              <Text color="font.tertiary">Click or drag an audio file here</Text>
            </>
          )}
          <Button size="small" variation="link" isDisabled={busy}>
            Browse files
          </Button>
        </Flex>
      </View>
      {sizeError && (
        <Alert
          variation="error"
          isDismissible
          onDismiss={() => setSizeError(false)}
          heading="File too large"
        >
          Maximum file size is 50 MB. Please choose a smaller file.
        </Alert>
      )}
    </Flex>
  );
}
