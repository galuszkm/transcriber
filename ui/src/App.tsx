import { TranscriberProvider, useTranscriber } from "./context/TranscriberContext";
import AudioUpload from "./components/AudioUpload";
import AudioRecorder from "./components/AudioRecorder";
import TranscriptDisplay from "./components/TranscriptDisplay";
import StatusBar from "./components/StatusBar";

function Controls() {
  const { audioFile, status, submit, cancel, reset } = useTranscriber();

  return (
    <div className="controls">
      <AudioUpload />
      <div className="btn-row">
        <AudioRecorder />
        <button
          className="btn btn-primary"
          onClick={submit}
          disabled={!audioFile || status === "transcribing"}
          type="button"
        >
          Transcribe
        </button>
        {status === "transcribing" && (
          <button className="btn btn-danger" onClick={cancel} type="button">
            Cancel
          </button>
        )}
        {(status === "done" || status === "error") && (
          <button className="btn" onClick={reset} type="button">
            Reset
          </button>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <TranscriberProvider>
      <div className="app">
        <h1>Transcriber</h1>
        <StatusBar />
        <Controls />
        <TranscriptDisplay />
      </div>
    </TranscriberProvider>
  );
}
