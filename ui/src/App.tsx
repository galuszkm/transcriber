import {
  ThemeProvider,
  createTheme,
  defaultDarkModeOverride,
  Flex,
  Heading,
  Card,
  Loader,
  Text,
} from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import { FiSun, FiMoon } from "react-icons/fi";
import { FaGithub } from "react-icons/fa";
import { TranscriberProvider, useTranscriber } from "./context/TranscriberContext";
import Controls from "./components/Controls";
import AudioPlayer from "./components/AudioPlayer";
import TranscriptDisplay from "./components/TranscriptDisplay";
import StatusBar from "./components/StatusBar";
import "./amplify-overwrite.css";

const theme = createTheme({ name: "app-theme", overrides: [defaultDarkModeOverride] });

const AppContent = ({ colorMode, toggleColorMode }: { colorMode: "light" | "dark"; toggleColorMode: () => void }) => {
  const { status, transcript, message, transcriptCollapsed } = useTranscriber();


  const renderHeader = () => (
    <header className="app-header">
      <div className="app-header-inner">
        <Heading level={4} className="app-heading">Transcription Service</Heading>
        <Flex alignItems="center" gap="0.75rem">
          <button
            onClick={toggleColorMode}
            aria-label={colorMode === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className="icon-btn"
          >
            {colorMode === "dark" ? <FiSun size={22} /> : <FiMoon size={22} />}
          </button>
          <a
            href="https://github.com/galuszkm/transcriber"
            target="_blank"
            rel="noreferrer"
            aria-label="GitHub repository"
            className="icon-btn"
          >
            <FaGithub size={22} />
          </a>
        </Flex>
      </div>
    </header>
  );

  const renderTranscribingCard = () => (
    <Card variation="outlined" className="transcript-card">
      <Flex
        direction="column"
        alignItems="center"
        justifyContent="center"
        style={{
          flex: 1,
          minHeight: transcriptCollapsed ? 67 : 200,
          height: transcriptCollapsed ? 67 : "unset",
        }}
        gap={transcriptCollapsed ? "0.25rem" : "1rem"}
      >
        <Loader size="large" style={{ width: "3rem", height: "3rem" }} />
        <Text color="font.tertiary">{message || "Transcribing…"}</Text>
      </Flex>
    </Card>
  );

  const renderIdleCard = () => (
    <Card variation="outlined" className="transcript-card">
      <Flex
        direction="column"
        alignItems="center"
        justifyContent="center"
        style={{
          flex: 1,
          minHeight: transcriptCollapsed ? 67 : 200,
          height: transcriptCollapsed ? 67 : "unset",
        }}
        gap="0.5rem"
      >
        <Text color="font.tertiary" fontSize="0.95rem">
          Upload or record audio and click Transcribe to see the transcript here.
        </Text>
      </Flex>
    </Card>
  );

  const renderTranscriptArea = () => {
    if (status === "transcribing") return renderTranscribingCard();
    if (status === "done" && transcript) return <TranscriptDisplay />;
    return renderIdleCard();
  };

  return (
    <>
      {renderHeader()}
      <Flex direction="column" className="app-shell" gap="0.75rem">
        <StatusBar />
        <div className="two-col">
          <div className="col-transcript">{renderTranscriptArea()}</div>
          <div className="col-sidebar">
            <Controls />
            <AudioPlayer />
          </div>
        </div>
      </Flex>
    </>
  );
};

const AppShell = () => {
  const { darkMode, setDarkMode } = useTranscriber();
  const colorMode = darkMode ? "dark" : "light";
  const toggleColorMode = () => setDarkMode(!darkMode);

  return (
    <ThemeProvider theme={theme} colorMode={colorMode}>
      <AppContent colorMode={colorMode} toggleColorMode={toggleColorMode} />
    </ThemeProvider>
  );
};

const App = () => (
  <TranscriberProvider>
    <AppShell />
  </TranscriberProvider>
);

export default App;
