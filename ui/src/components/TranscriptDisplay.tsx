import { Card, Heading, Tabs, Text, Flex } from "@aws-amplify/ui-react";
import { FiChevronDown, FiChevronUp } from "react-icons/fi";
import { useTranscriber } from "../context/TranscriberContext";
import TranscriptSegments from "./TranscriptSegments";
import TranscriptScript from "./TranscriptScript";
import TranscriptPlainText from "./TranscriptPlainText";
import TranscriptToolbar from "./TranscriptToolbar";
import { formatTime, toPlainText } from "../utils/format";
import type { TranscriptView } from "../types";

export default function TranscriptDisplay() {
  const { transcript, view, setView, transcriptCollapsed, setTranscriptCollapsed } = useTranscriber();

  if (!transcript) return null;

  const data = transcript;
  const hasSpeakers = data.segments.some((s) => s.speaker);

  const renderHeader = () => (
    <>
      <Flex justifyContent="space-between" alignItems="center" wrap="wrap" gap="0.5rem">
        <Flex alignItems="center" gap="0.4rem">
          <button
            className="icon-btn"
            onClick={() => setTranscriptCollapsed(!transcriptCollapsed)}
            aria-label={transcriptCollapsed ? "Expand transcript" : "Collapse transcript"}
            style={{ color: "inherit" }}
          >
            {transcriptCollapsed ? <FiChevronDown size={18} /> : <FiChevronUp size={18} />}
          </button>
          <Heading level={4}>Transcript</Heading>
        </Flex>
        <TranscriptToolbar transcript={data} />
      </Flex>
      <Text fontSize="0.85rem" color="font.tertiary">
        Language: {data.language} &middot; Duration: {formatTime(data.duration)}
      </Text>
    </>
  );

  const renderTabs = () => (
    <Tabs.Container value={view} onValueChange={(val) => setView(val as TranscriptView)}>
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

  return (
    <Card variation="outlined" className="transcript-card">
      <Flex direction="column" gap="0.75rem" style={{ flex: 1, minHeight: 0 }}>
        {renderHeader()}
        {!transcriptCollapsed && renderTabs()}
      </Flex>
    </Card>
  );
}
