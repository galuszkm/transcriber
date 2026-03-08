import { Heading, Text, View } from "@aws-amplify/ui-react";
import type { Segment } from "../types";

interface Props {
  segments: Segment[];
}

/** Group consecutive segments by speaker. */
function groupBySpeaker(segments: Segment[]) {
  const groups: { speaker: string; lines: string[] }[] = [];
  let current: { speaker: string; lines: string[] } | null = null;

  for (const seg of segments) {
    const speaker = seg.speaker ?? "Speaker";
    if (!current || current.speaker !== speaker) {
      current = { speaker, lines: [] };
      groups.push(current);
    }
    current.lines.push(seg.text.trim());
  }

  return groups;
}

export default function TranscriptScript({ segments }: Props) {
  const groups = groupBySpeaker(segments);

  return (
    <View className="transcript-script">
      {groups.map((group, i) => (
        <View key={i} className="script-block">
          <Heading level={5} className="script-speaker">
            {group.speaker}
          </Heading>
          <Text className="script-text">
            {group.lines.join(" ")}
          </Text>
        </View>
      ))}
    </View>
  );
}
