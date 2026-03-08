import { Alert } from "@aws-amplify/ui-react";
import { useTranscriber } from "../context/TranscriberContext";

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
