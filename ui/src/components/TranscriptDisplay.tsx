import { useTranscriber } from "../context/TranscriberContext";

/** Format seconds to mm:ss display. */
function ts(sec: number): string {
  const m = Math.floor(sec / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(sec % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

export default function TranscriptDisplay() {
  const { transcript } = useTranscriber();

  if (!transcript) return null;

  return (
    <div className="transcript">
      <h2>Transcript</h2>
      <p className="transcript-meta">
        Language: {transcript.language} &middot; Duration:{" "}
        {ts(transcript.duration)}
      </p>
      {transcript.segments.map((seg, i) => (
        <div className="segment" key={i}>
          <span className="time">
            [{ts(seg.start)}&ndash;{ts(seg.end)}]
          </span>
          {seg.speaker && <span className="speaker">{seg.speaker}:</span>}
          <span>{seg.text}</span>
        </div>
      ))}
    </div>
  );
}
