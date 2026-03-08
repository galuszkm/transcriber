import { Card, Heading, Tabs, Text, Flex } from "@aws-amplify/ui-react";
import { useTranscriber } from "../context/TranscriberContext";
import TranscriptSegments from "./TranscriptSegments";
import TranscriptScript from "./TranscriptScript";
import TranscriptPlainText from "./TranscriptPlainText";
import TranscriptToolbar from "./TranscriptToolbar";
import { formatTime, toPlainText } from "../utils/format";
import type { TranscriptView } from "../context/TranscriberContext";

export default function TranscriptDisplay() {
  const { transcript, view, setView } = useTranscriber();

  if (!transcript) return null;

  const hasSpeakers = transcript.segments.some((s) => s.speaker);

  return (
    <Card variation="outlined" className="transcript-card">
      <Flex direction="column" gap="0.75rem">
        <Flex justifyContent="space-between" alignItems="center" wrap="wrap">
          <Heading level={4}>Transcript</Heading>
          <TranscriptToolbar transcript={transcript} />
        </Flex>

        <Text fontSize="0.85rem" color="font.tertiary">
          Language: {transcript.language} &middot; Duration:{" "}
          {formatTime(transcript.duration)}
        </Text>

        <Tabs.Container
          value={view}
          onValueChange={(val) => setView(val as TranscriptView)}
        >
          <Tabs.List>
            <Tabs.Item value="segments">Segments</Tabs.Item>
            {hasSpeakers && (
              <Tabs.Item value="script">Script</Tabs.Item>
            )}
            <Tabs.Item value="plain">Plain Text</Tabs.Item>
          </Tabs.List>

          <Tabs.Panel value="segments">
            <TranscriptSegments segments={transcript.segments} />
          </Tabs.Panel>

          {hasSpeakers && (
            <Tabs.Panel value="script">
              <TranscriptScript segments={transcript.segments} />
            </Tabs.Panel>
          )}

          <Tabs.Panel value="plain">
            <TranscriptPlainText text={toPlainText(transcript)} />
          </Tabs.Panel>
        </Tabs.Container>
      </Flex>
    </Card>
  );
}
