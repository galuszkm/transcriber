import { useEffect, useMemo, useRef } from "react";
import { Card, Flex, Text } from "@aws-amplify/ui-react";
import { FiMusic } from "react-icons/fi";
import { useTranscriber } from "../context/TranscriberContext";

export default function AudioPlayer() {
  const { audioFile } = useTranscriber();
  const audioRef = useRef<HTMLAudioElement>(null);

  const objectUrl = useMemo(() => {
    if (!audioFile) return null;
    return URL.createObjectURL(audioFile);
  }, [audioFile]);

  useEffect(() => {
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [objectUrl]);

  if (!audioFile) return null;

  const file = audioFile;

  const renderHeader = () => (
    <Flex justifyContent="space-between" alignItems="center" wrap="wrap" gap="0.5rem">
      <Flex alignItems="center" gap="0.35rem">
        <FiMusic size={14} />
        <Text fontWeight="bold" fontSize="0.9rem">Audio</Text>
      </Flex>
      <Text fontSize="0.8rem" color="font.tertiary">{file.name}</Text>
    </Flex>
  );

  return (
    <Card variation="outlined" className="audio-player-card">
      <Flex direction="column" gap="0.5rem">
        {renderHeader()}
        {objectUrl && (
          <audio ref={audioRef} controls src={objectUrl} style={{ width: "100%" }} data-testid="audio-player" />
        )}
      </Flex>
    </Card>
  );
}
