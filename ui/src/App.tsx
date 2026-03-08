import { ThemeProvider, Flex, Heading, Card, Button, Loader } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import { TranscriberProvider, useTranscriber } from "./context/TranscriberContext";
import AudioUpload from "./components/AudioUpload";
import AudioRecorder from "./components/AudioRecorder";
import AudioPlayer from "./components/AudioPlayer";
import TranscriptDisplay from "./components/TranscriptDisplay";
import StatusBar from "./components/StatusBar";

function Controls() {
  const { audioFile, status, submit, cancel, reset } = useTranscriber();

  return (
    <Card variation="outlined">
      <Flex direction="column" gap="1rem">
        <AudioUpload />
        <Flex alignItems="center" gap="0.5rem" wrap="wrap">
          <AudioRecorder />
          <Button
            variation="primary"
            size="small"
            onClick={submit}
            isDisabled={!audioFile || status === "transcribing"}
            isLoading={status === "transcribing"}
            loadingText="Transcribing..."
          >
            Transcribe
          </Button>
          {status === "transcribing" && (
            <Button variation="destructive" size="small" onClick={cancel}>
              Cancel
            </Button>
          )}
          {(status === "done" || status === "error") && (
            <Button size="small" onClick={reset}>
              Reset
            </Button>
          )}
        </Flex>
      </Flex>
    </Card>
  );
}

function AppContent() {
  const { status } = useTranscriber();

  return (
    <Flex direction="column" maxWidth="800px" margin="0 auto" padding="2rem 1rem" gap="1rem">
      <Heading level={3}>Transcriber</Heading>
      <StatusBar />
      <Controls />
      {status === "transcribing" && (
        <Flex justifyContent="center" padding="1rem">
          <Loader size="large" />
        </Flex>
      )}
      <TranscriptDisplay />
      <AudioPlayer />
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
