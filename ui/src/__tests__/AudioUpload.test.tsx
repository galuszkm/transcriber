import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import AudioUpload from "../components/AudioUpload";
import { TranscriberProvider } from "../context/TranscriberContext";

function renderWithProvider() {
  return render(
    <TranscriberProvider>
      <AudioUpload />
    </TranscriberProvider>,
  );
}

describe("AudioUpload", () => {
  it("shows placeholder text when no file is selected", () => {
    renderWithProvider();
    expect(screen.getByText(/click or drop an audio file here/i)).toBeInTheDocument();
  });

  it("shows file name after selecting a file", async () => {
    const user = userEvent.setup();
    renderWithProvider();

    const file = new File(["audio"], "test.mp3", { type: "audio/mpeg" });
    const input = screen.getByTestId("file-input");
    await user.upload(input, file);

    expect(screen.getByText("test.mp3")).toBeInTheDocument();
  });
});
