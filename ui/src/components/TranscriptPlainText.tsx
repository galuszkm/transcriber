import { TextAreaField } from "@aws-amplify/ui-react";

interface Props {
  text: string;
}

export default function TranscriptPlainText({ text }: Props) {
  return (
    <TextAreaField
      label=""
      labelHidden
      value={text}
      rows={16}
      isReadOnly
      fontFamily="monospace"
      fontSize="0.875rem"
      className="transcript-plain"
    />
  );
}
