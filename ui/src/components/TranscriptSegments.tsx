import { View, Text } from "@aws-amplify/ui-react";
import type { Segment } from "../types";
import { formatTime } from "../utils/format";

/** Extract a 0-based speaker index (mod 5) from strings like "SPEAKER_2". */
const speakerIdx = (speaker: string): number => {
  const m = speaker.match(/(\d+)$/);
  return m ? Number(m[1]) % 5 : 0;
};

interface Props {
  segments: Segment[];
}

/**
 * Renders transcript segments as timestamped rows.
 *
 * Each row shows `[start-end]`, an optional speaker label, and the text.
 */
export default function TranscriptSegments({ segments }: Props) {
  return (
    <View className="transcript-segments">
      {segments.map((seg, i) => (
        <View key={i} className="segment-row">
          <Text
            className="segment-time"
            fontFamily="monospace"
            fontSize="0.8rem"
          >
            [{formatTime(seg.start)}-{formatTime(seg.end)}]
          </Text>
          {seg.speaker && (
            <Text as="span" className="segment-speaker" fontWeight="bold" data-speaker-idx={speakerIdx(seg.speaker)}>
              {seg.speaker}:
            </Text>
          )}
          <Text as="span">{seg.text}</Text>
        </View>
      ))}
    </View>
  );
}
