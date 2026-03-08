import { useEffect, useMemo, useRef } from "react";
import { Button, Card, Flex, Text } from "@aws-amplify/ui-react";
import { FiMusic, FiDownload } from "react-icons/fi";
import { useTranscriber } from "../context/TranscriberContext";
import { downloadBlob } from "../utils/format";

export default function AudioPlayer() {
  const { audioFile, status } = useTranscriber();
  const audioRef = useRef<HTMLAudioElement>(null);

  const objectUrl = useMemo(() => {
    if (!audioFile) return null;
    return URL.createObjectURL(audioFile);
  }, [audioFile]);

  // Revoke old object URL on change or unmount.
  useEffect(() => {
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [objectUrl]);

  if (!audioFile || status !== "done") return null;

  const handleDownload = () => {
    downloadBlob(audioFile, audioFile.name);
  };

  return (
    <Card variation="outlined" className="audio-player-card">
      <Flex direction="column" gap="0.5rem">
        <Flex justifyContent="space-between" alignItems="center" wrap="wrap" gap="0.5rem">
          <Flex alignItems="center" gap="0.35rem">
            <FiMusic size={14} />
            <Text fontWeight="bold" fontSize="0.9rem">Audio</Text>
          </Flex>
          <Flex alignItems="center" gap="0.5rem" wrap="wrap">
            <Text fontSize="0.8rem" color="font.tertiary">
              {audioFile.name}
            </Text>
            <Button size="small" variation="link" onClick={handleDownload} className="btn-icon">
              <FiDownload size={14} />
              Download
            </Button>
          </Flex>
        </Flex>
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
