import { Card, Heading, Tabs, Text, Flex } from "@aws-amplify/ui-react";
import { useTranscriber } from "../context/TranscriberContext";
import TranscriptSegments from "./TranscriptSegments";
import TranscriptScript from "./TranscriptScript";
import TranscriptPlainText from "./TranscriptPlainText";
import TranscriptToolbar from "./TranscriptToolbar";
import { formatTime, toPlainText } from "../utils/format";
import type { TranscriptView } from "../context/TranscriberContext";

/**
 * Renders the completed transcript in a tabbed card.
 *
 * Three views: Segments (timestamped rows), Script (movie-style grouped by
 * speaker), and Plain Text (read-only textarea). The Script tab only appears
 * when diarization detected speakers in the segments.
 */
export default function TranscriptDisplay() {
  const { transcript, view, setView } = useTranscriber();

  if (!transcript) return null;

  // Local const so TypeScript narrows the type inside nested render functions.
  const data = transcript;
  const hasSpeakers = data.segments.some((s) => s.speaker);

  /** Render the card header with title and copy/download toolbar. */
  function renderHeader() {
    return (
      <>
        <Flex
          justifyContent="space-between"
          alignItems="center"
          wrap="wrap"
          gap="0.5rem"
        >
          <Heading level={4}>Transcript</Heading>
          <TranscriptToolbar transcript={data} />
        </Flex>
        <Text fontSize="0.85rem" color="font.tertiary">
          Language: {data.language} &middot; Duration:{" "}
          {formatTime(data.duration)}
        </Text>
      </>
    );
  }

  /** Render the tab list and panels for the three transcript views. */
  function renderTabs() {
    return (
      <Tabs.Container
        value={view}
        onValueChange={(val) => setView(val as TranscriptView)}
      >
        <Tabs.List>
          <Tabs.Item value="segments">Segments</Tabs.Item>
          {hasSpeakers && <Tabs.Item value="script">Script</Tabs.Item>}
          <Tabs.Item value="plain">Plain Text</Tabs.Item>
        </Tabs.List>

        <Tabs.Panel value="segments">
          <TranscriptSegments segments={data.segments} />
        </Tabs.Panel>

        {hasSpeakers && (
          <Tabs.Panel value="script">
            <TranscriptScript segments={data.segments} />
          </Tabs.Panel>
        )}

        <Tabs.Panel value="plain">
          <TranscriptPlainText text={toPlainText(data)} />
        </Tabs.Panel>
      </Tabs.Container>
    );
  }

  return (
    <Card variation="outlined" className="transcript-card">
      <Flex direction="column" gap="0.75rem" style={{ flex: 1, minHeight: 0 }}>
        {renderHeader()}
        {renderTabs()}
      </Flex>
    </Card>
  );
}
