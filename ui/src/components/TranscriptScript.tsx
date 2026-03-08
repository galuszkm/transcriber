import { Heading, Text, View } from "@aws-amplify/ui-react";
import type { Segment } from "../types";

const speakerIdx = (speaker: string): number => {
  const m = speaker.match(/(\d+)$/);
  return m ? Number(m[1]) % 5 : 0;
};

interface Props {
  segments: Segment[];
}

/** A group of consecutive lines from the same speaker. */
interface SpeakerGroup {
  speaker: string;
  lines: string[];
}

/**
 * Group consecutive segments by speaker for movie-script rendering.
 *
 * Adjacent segments from the same speaker are merged into one block
 * so the output reads like a screenplay.
 *
 * @param segments - Transcript segments, each with optional speaker.
 * @returns Array of speaker groups with their concatenated lines.
 */
const groupBySpeaker = (segments: Segment[]): SpeakerGroup[] => {
  const groups: SpeakerGroup[] = [];
  let current: SpeakerGroup | null = null;

  for (const seg of segments) {
    const speaker = seg.speaker ?? "Speaker";
    if (!current || current.speaker !== speaker) {
      current = { speaker, lines: [] };
      groups.push(current);
    }
    current.lines.push(seg.text.trim());
  }

  return groups;
};

/**
 * Renders a movie-script-style transcript grouped by speaker.
 *
 * Each speaker gets an uppercase heading, followed by their concatenated text.
 * Only meaningful when diarization is enabled.
 */
const TranscriptScript = ({ segments }: Props) => {
  const groups = groupBySpeaker(segments);

  return (
    <View className="transcript-script">
      {groups.map((group, i) => (
        <View key={i} className="script-block">
          <Heading level={5} className="script-speaker" data-speaker-idx={speakerIdx(group.speaker)}>
            {group.speaker}
          </Heading>
          <Text className="script-text">{group.lines.join(" ")}</Text>
        </View>
      ))}
    </View>
  );
};

export default TranscriptScript;
