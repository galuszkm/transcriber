import { useTranscriber } from "../context/TranscriberContext";

export default function StatusBar() {
  const { status, message } = useTranscriber();

  if (!message) return null;

  const className =
    status === "error"
      ? "status-bar error"
      : status === "done"
        ? "status-bar success"
        : "status-bar info";

  return (
    <div className={className} role="status">
      {message}
    </div>
  );
}
