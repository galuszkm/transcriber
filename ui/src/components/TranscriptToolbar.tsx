import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Flex, Menu, MenuItem } from "@aws-amplify/ui-react";
import { FiCopy, FiCheck, FiDownload } from "react-icons/fi";
import type { TranscribeResponse } from "../types";
import {
  toPlainText,
  toMarkdown,
  toFullJson,
  toSegmentsJson,
  copyToClipboard,
  downloadFile,
} from "../utils/format";

interface Props {
  transcript: TranscribeResponse;
}

export default function TranscriptToolbar({ transcript }: Props) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear timeout on unmount.
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleCopy = useCallback(async (text: string) => {
    const ok = await copyToClipboard(text);
    if (ok) {
      setCopied(true);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setCopied(false), 2000);
    }
  }, []);

  return (
    <Flex gap="0.25rem" alignItems="center">
      <Menu trigger={
        <Button size="small" variation="link" className="btn-icon">
          {copied ? <FiCheck /> : <FiCopy />}
          {copied ? "Copied" : "Copy"}
        </Button>
      }>
        <MenuItem onClick={() => handleCopy(toPlainText(transcript))}>
          Plain text
        </MenuItem>
        <MenuItem onClick={() => handleCopy(toMarkdown(transcript))}>
          Markdown
        </MenuItem>
        <MenuItem onClick={() => handleCopy(toSegmentsJson(transcript.segments))}>
          Segments (JSON)
        </MenuItem>
        <MenuItem onClick={() => handleCopy(toFullJson(transcript))}>
          Full response (JSON)
        </MenuItem>
      </Menu>

      <Menu trigger={
        <Button size="small" variation="link" className="btn-icon">
          <FiDownload />
          Download
        </Button>
      }>
        <MenuItem
          onClick={() => downloadFile(toPlainText(transcript), "transcript.txt")}
        >
          Plain text (.txt)
        </MenuItem>
        <MenuItem
          onClick={() =>
            downloadFile(toMarkdown(transcript), "transcript.md", "text/markdown")
          }
        >
          Markdown (.md)
        </MenuItem>
        <MenuItem
          onClick={() =>
            downloadFile(
              toFullJson(transcript),
              "transcript.json",
              "application/json",
            )
          }
        >
          Full response (.json)
        </MenuItem>
      </Menu>
    </Flex>
  );
}
