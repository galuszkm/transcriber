import {
  ThemeProvider,
  Flex,
  Heading,
  Card,
  Button,
  Loader,
  CheckboxField,
  Text,
} from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import { FiSend, FiXCircle, FiRotateCcw } from "react-icons/fi";
import { TranscriberProvider, useTranscriber } from "./context/TranscriberContext";
import AudioUpload from "./components/AudioUpload";
import AudioRecorder from "./components/AudioRecorder";
import AudioPlayer from "./components/AudioPlayer";
import TranscriptDisplay from "./components/TranscriptDisplay";
import StatusBar from "./components/StatusBar";

/** Sidebar with upload, action buttons, diarize toggle, and audio player. */
function Controls() {
  const { audioFile, status, diarize, setDiarize, submit, cancel, reset } =
    useTranscriber();

  /** Render the action buttons row (Record, Transcribe, Cancel, Reset). */
  function renderActions() {
    return (
      <Flex alignItems="center" gap="0.5rem" wrap="wrap">
        <AudioRecorder />
        <Button
          variation="primary"
          size="small"
          onClick={submit}
          isDisabled={!audioFile || status === "transcribing"}
          isLoading={status === "transcribing"}
          loadingText="Transcribing..."
          className="btn-icon"
        >
          <FiSend size={14} />
          Transcribe
        </Button>
        {status === "transcribing" && (
          <Button
            variation="destructive"
            size="small"
            onClick={cancel}
            className="btn-icon"
          >
            <FiXCircle size={14} />
            Cancel
          </Button>
        )}
        {(status === "done" || status === "error") && (
          <Button size="small" onClick={reset} className="btn-icon">
            <FiRotateCcw size={14} />
            Reset
          </Button>
        )}
      </Flex>
    );
  }

  return (
    <Card variation="outlined">
      <Flex direction="column" gap="1rem">
        <AudioUpload />
        {renderActions()}
        <CheckboxField
          label="Enable speaker diarization"
          name="diarize"
          checked={diarize}
          onChange={(e) => setDiarize(e.target.checked)}
          size="small"
        />
      </Flex>
    </Card>
  );
}

/**
 * Placeholder shown in the transcript column before any transcription.
 * Gives the user context about where the transcript will appear.
 */
function TranscriptPlaceholder() {
  return (
    <Card variation="outlined" className="transcript-card">
      <Flex
        direction="column"
        alignItems="center"
        justifyContent="center"
        style={{ flex: 1, minHeight: 200 }}
        gap="0.5rem"
      >
        <Text color="font.tertiary" fontSize="0.95rem">
          Upload or record audio and click Transcribe to see the transcript here.
        </Text>
      </Flex>
    </Card>
  );
}

/** Main application layout — always two-column with transcript left, controls right. */
function AppContent() {
  const { status, transcript } = useTranscriber();
  const hasTranscript = status === "done" && transcript;

  /** Render the transcript column content based on current state. */
  function renderTranscript() {
    if (status === "transcribing") {
      return (
        <Card variation="outlined" className="transcript-card">
          <Flex
            direction="column"
            alignItems="center"
            justifyContent="center"
            style={{ flex: 1, minHeight: 200 }}
            gap="1rem"
          >
            <Loader size="large" />
            <Text color="font.tertiary">Transcribing...</Text>
          </Flex>
        </Card>
      );
    }

    if (hasTranscript) {
      return <TranscriptDisplay />;
    }

    return <TranscriptPlaceholder />;
  }

  return (
    <Flex direction="column" className="app-shell" gap="0.75rem">
      <Heading level={3}>Transcriber</Heading>
      <StatusBar />

      <div className="two-col">
        <div className="col-transcript">{renderTranscript()}</div>
        <div className="col-sidebar">
          <Controls />
          <AudioPlayer />
        </div>
      </div>
    </Flex>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <TranscriberProvider>
        <AppContent />
      </TranscriberProvider>
    </ThemeProvider>
  );
}
