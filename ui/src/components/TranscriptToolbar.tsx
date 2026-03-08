import { useState } from "react";
import { Button, Flex, Menu, MenuItem } from "@aws-amplify/ui-react";
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

  const handleCopy = async (text: string) => {
    const ok = await copyToClipboard(text);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Flex gap="0.5rem" wrap="wrap">
      <Menu trigger={
        <Button size="small" variation="link">
          {copied ? "\u2713 Copied" : "\u2398 Copy"}
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
        <Button size="small" variation="link">
          &#8615; Download
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
