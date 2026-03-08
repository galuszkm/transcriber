import { TextAreaField } from "@aws-amplify/ui-react";

interface Props {
  text: string;
}

export default function TranscriptPlainText({ text }: Props) {
  return (
    <div className="transcript-plain">
      <TextAreaField
        label=""
        labelHidden
        value={text}
        rows={16}
        isReadOnly
        fontFamily="monospace"
        fontSize="0.875rem"
      />
    </div>
  );
}
