import { useEffect, useMemo, useRef } from "react";
import { Button, Card, Flex, Text } from "@aws-amplify/ui-react";
import { useTranscriber } from "../context/TranscriberContext";

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
    if (!objectUrl) return;
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = audioFile.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <Card variation="outlined" className="audio-player-card">
      <Flex direction="column" gap="0.5rem">
        <Flex justifyContent="space-between" alignItems="center">
          <Text fontWeight="bold" fontSize="0.9rem">
            &#9835; Audio
          </Text>
          <Flex gap="0.5rem">
            <Text fontSize="0.8rem" color="font.tertiary">
              {audioFile.name}
            </Text>
            <Button size="small" variation="link" onClick={handleDownload}>
              &#8615; Download audio
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
