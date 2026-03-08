import { Card, Flex, Button, CheckboxField } from "@aws-amplify/ui-react";
import { FiSend, FiXCircle, FiRotateCcw, FiInfo } from "react-icons/fi";
import { useTranscriber } from "../context/TranscriberContext";
import AudioUpload from "./AudioUpload";
import AudioRecorder from "./AudioRecorder";

export default function Controls() {
  const { audioFile, status, isRecording, diarize, setDiarize, autoCopy, setAutoCopy, showDropzone, setShowDropzone, submit, cancel, reset } =
    useTranscriber();

  const renderActionButtons = () => (
    <Flex alignItems="center" gap="0.5rem" justifyContent="flex-end">
      <Button
        variation="primary"
        size="small"
        onClick={submit}
        isDisabled={!audioFile || status === "transcribing"}
        isLoading={status === "transcribing"}
        loadingText="Processing…"
        className="btn-icon"
      >
        <FiSend size={14} />
        Transcribe
      </Button>
      {status === "transcribing" && (
        <Button variation="destructive" size="small" onClick={cancel} className="btn-icon">
          <FiXCircle size={14} />
          Cancel
        </Button>
      )}
      {(status === "done" || status === "error") && (
        <Button size="small" onClick={reset} isDisabled={isRecording} className="btn-icon">
          <FiRotateCcw size={14} />
          Reset
        </Button>
      )}
    </Flex>
  );

  const renderOptions = () => (
    <Flex alignItems="center" gap="1.25rem" wrap="wrap" width="100%">
      <Flex alignItems="center" gap="0.35rem">
        <CheckboxField
          label="Diarize"
          name="diarize"
          checked={diarize}
          onChange={(e) => setDiarize(e.target.checked)}
          size="small"
        />
        <span className="info-icon">
          <FiInfo size={13} />
          <span className="info-tooltip">
            Identifies and separates individual speakers in the audio, labeling each segment by speaker
          </span>
        </span>
      </Flex>
      <Flex alignItems="center" gap="0.35rem">
        <CheckboxField
          label="Auto-copy"
          name="autoCopy"
          checked={autoCopy}
          onChange={(e) => setAutoCopy(e.target.checked)}
          size="small"
        />
        <span className="info-icon">
          <FiInfo size={13} />
          <span className="info-tooltip">
            Automatically copies the plain text transcript to your clipboard when transcription completes
          </span>
        </span>
      </Flex>
      <div style={{ marginLeft: "auto" }}>
        <CheckboxField
          label="Upload file"
          name="showDropzone"
          checked={showDropzone}
          onChange={(e) => setShowDropzone(e.target.checked)}
          size="small"
        />
      </div>
    </Flex>
  );

  return (
    <Card variation="outlined" style={{ userSelect: "none" }}>
      <Flex direction="column" gap="1rem">
        {renderOptions()}
        <div style={{ display: showDropzone ? undefined : "none" }}>
          <AudioUpload />
        </div>
        <Flex alignItems="center" justifyContent="space-between" wrap="wrap" gap="0.5rem">
          <AudioRecorder />
          {renderActionButtons()}
        </Flex>
      </Flex>
    </Card>
  );
}
