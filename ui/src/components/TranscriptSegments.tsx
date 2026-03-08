import { View, Text } from "@aws-amplify/ui-react";
import type { Segment } from "../types";
import { formatTime } from "../utils/format";

interface Props {
  segments: Segment[];
}

export default function TranscriptSegments({ segments }: Props) {
  return (
    <View className="transcript-segments">
      {segments.map((seg, i) => (
        <View key={i} className="segment-row">
          <Text className="segment-time" fontFamily="monospace" fontSize="0.8rem">
            [{formatTime(seg.start)}-{formatTime(seg.end)}]
          </Text>
          {seg.speaker && (
            <Text as="span" className="segment-speaker" fontWeight="bold">
              {seg.speaker}:
            </Text>
          )}
          <Text as="span">{seg.text}</Text>
        </View>
      ))}
    </View>
  );
}
