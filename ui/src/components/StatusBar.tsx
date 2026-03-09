import { Alert } from "@aws-amplify/ui-react";
import { useTranscriber } from "../context/TranscriberContext";

/**
 * Status alert bar showing the current transcription state.
 *
 * Displays success, error, or info messages. Hidden when there's no message.
 */
export default function StatusBar() {
  const { status, message } = useTranscriber();

  if (!message) return null;

  const variation =
    status === "error"
      ? "error"
      : status === "done"
        ? "success"
        : "info";

  return (
    <Alert variation={variation} isDismissible={false} role="status">
      {message}
    </Alert>
  );
}
