import { useEffect, useMemo, useRef } from "react";
import { Button, Card, Flex, Text } from "@aws-amplify/ui-react";
import { FiMusic, FiDownload } from "react-icons/fi";
import { useTranscriber } from "../context/TranscriberContext";
import { downloadBlob } from "../utils/format";

/**
 * Audio playback card with native controls and a download button.
 *
 * Only renders when an audio file is loaded (uploaded or recorded).
 * Uses a frontend Blob URL so no server round-trip is needed for playback.
 */
export default function AudioPlayer() {
  const { audioFile } = useTranscriber();
  const audioRef = useRef<HTMLAudioElement>(null);

  // Create an object URL for the current audio file.
  const objectUrl = useMemo(() => {
    if (!audioFile) return null;
    return URL.createObjectURL(audioFile);
  }, [audioFile]);

  // Revoke the old object URL when the file changes or on unmount to avoid memory leaks.
  useEffect(() => {
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [objectUrl]);

  if (!audioFile) return null;

  // Local const so TypeScript narrows the type inside nested render functions.
  const file = audioFile;

  /** Trigger a browser download of the current audio file. */
  const handleDownload = () => {
    downloadBlob(file, file.name);
  };

  /** Render the header row with title, filename, and download button. */
  function renderHeader() {
    return (
      <Flex
        justifyContent="space-between"
        alignItems="center"
        wrap="wrap"
        gap="0.5rem"
      >
        <Flex alignItems="center" gap="0.35rem">
          <FiMusic size={14} />
          <Text fontWeight="bold" fontSize="0.9rem">
            Audio
          </Text>
        </Flex>
        <Flex alignItems="center" gap="0.5rem" wrap="wrap">
          <Text fontSize="0.8rem" color="font.tertiary">
            {file.name}
          </Text>
          <Button
            size="small"
            variation="link"
            onClick={handleDownload}
            className="btn-icon"
          >
            <FiDownload size={14} />
            Download
          </Button>
        </Flex>
      </Flex>
    );
  }

  return (
    <Card variation="outlined" className="audio-player-card">
      <Flex direction="column" gap="0.5rem">
        {renderHeader()}
        {objectUrl && (
          <audio
            ref={audioRef}
            controls
            src={objectUrl}
            style={{ width: "100%" }}
            data-testid="audio-player"
          />
        )}
      </Flex>
    </Card>
  );
}
