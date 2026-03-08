import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StatusBar from "./StatusBar";
import { TranscriberProvider } from "../context/TranscriberContext";

describe("StatusBar", () => {
  it("renders nothing when there is no message", () => {
    const { container } = render(
      <TranscriberProvider>
        <StatusBar />
      </TranscriberProvider>,
    );
    expect(container.querySelector("[role='status']")).toBeNull();
  });
});
