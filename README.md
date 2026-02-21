# Transcriber

Local audio transcription tool powered by **WhisperX**. Transcribes meeting recordings with word-level timestamps and optional speaker diarization. Everything runs locally — no data leaves your machine.

## Features

- **WhisperX-powered** transcription with word-level alignment
- **Speaker diarization** — identifies who said what (optional, requires free HuggingFace token)
- **Markdown output** — clean transcript ready to pass to an LLM for summarization
- **Configurable models** — tiny through large-v3, CPU or CUDA
- **Fully offline** after initial model download


## Architecture

The code is split into four sub-packages. The boundary rule is simple: ML model calls stay in `pipeline/`, data movement stays in `io/`, shared types and config stay in `core/`, and everything the user directly interacts with stays in `cli/`. This means replacing WhisperX with a different backend only touches `pipeline/`.

### Sub-packages

| Package | What it contains | Key responsibility |
|---------|-----------------|-------------------|
| `core/` | Config dataclass, Pydantic result/segment models | Single source of truth for settings and data shapes shared across all other packages |
| `io/` | Audio loader, transcript writer | Format-level I/O with no model dependency — decodes audio, writes Markdown/JSON |
| `pipeline/` | Transcription orchestrator, alignment, diarization | All ML inference; owns the WhisperX and pyannote calls |
| `cli/` | Argument parser, Rich display, entry point | User interface only; delegates everything to `pipeline/` and `io/` |

### Processing pipeline

`TranscriptionPipeline` (in `pipeline/`) sequences the stages below. The Whisper model is loaded once on the first call and reused, so processing multiple files in one session is cheap.

1. **Audio decoding** (`io/`) — any supported container is decoded into a 16 kHz mono float32 array. This is the exact format WhisperX requires, so no conversion happens inside the model code.
2. **ASR transcription** (`pipeline/`) — WhisperX batch inference. Produces text segments with coarse sentence-level timestamps.
3. **Word-level alignment** (`pipeline/`) — a separate forced-alignment model (wav2vec2-based) refines those coarse timestamps to individual words. This is a distinct model pass, not part of transcription — it needs the text as input and produces the precise boundaries that make diarization reliable.
4. **Speaker diarization** (`pipeline/`, optional) — pyannote detects speaker-turn boundaries in the audio, then WhisperX assigns a speaker label to each word. A custom re-segmentation pass splits any segment that crosses a speaker boundary, so every output segment belongs to exactly one speaker. WhisperX's default majority-vote assignment does not do this split. If diarization fails for any reason, the pipeline falls back to the undiarized transcript rather than crashing.
5. **Output rendering** (`io/`) — the typed result is serialised to Markdown or JSON. Speaker turns are grouped into labelled blocks with timestamps, ready to paste into an LLM.


## Prerequisites

### 1. uv (package manager)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) — it manages Python itself, so no separate Python installation is needed:

```powershell
# Linux / macOS (bash)
curl -Ls https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

`uv sync` will automatically download and use Python 3.12 as declared in `pyproject.toml`.

### 2. FFmpeg

WhisperX and PyAV require FFmpeg libraries at runtime.

**Windows:**

1. Download the **full build** (not "essentials") from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-7.1.1-full_build-shared.7z) — get `ffmpeg-release-full.7z`
2. Extract to a permanent location, e.g. `C:\ffmpeg`
3. Add the `bin` folder to your system `PATH`:

```powershell
# Run as Administrator
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "Machine") + ";C:\ffmpeg\bin",
    "Machine"
)
```

4. Verify:

```powershell
ffmpeg -version
```

**Linux / macOS:**

```bash
sudo apt install ffmpeg   # Ubuntu/Debian
brew install ffmpeg       # macOS
```

### 3. NVIDIA GPU + CUDA (optional, recommended)

For GPU-accelerated transcription:

- NVIDIA GPU with compute capability >= 7.0 (for float16)
- [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
- Latest [NVIDIA GPU drivers](https://www.nvidia.com/drivers)

Verify:

```powershell
nvidia-smi
```

> CPU mode works but is significantly slower (~10x).


## Installation

```bash
git clone <repo-url>
cd transcriber

# Installs Python 3.12, all dependencies, and git hooks
uv run just install
```

## Configuration

Create a `.env` file in the project root — the app loads it automatically:

```env
# Required only for speaker diarization (--diarize flag)
HF_TOKEN=hf_your_token_here
```

### Getting a HuggingFace token (for speaker diarization)

Diarization models are **free and MIT-licensed**, but gated (accept terms once):

1. Create a free account at [huggingface.co](https://huggingface.co/join)
2. Create a **Read** token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
3. Visit [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) and click **"Agree and access repository"**
4. Add the token to `.env`

Models are downloaded once (~600MB) on first use and cached in `.cache/huggingface/`. Fully offline after that.


## Usage

```bash
# Basic transcription (CPU, base model, markdown output)
uv run transcriber recording.wav

# GPU with large model (recommended for quality)
uv run transcriber recording.mp3 -m large-v3 -d cuda

# With speaker detection
uv run transcriber meeting.mp3 -m large-v3 -d cuda --diarize

# Specify language (skips auto-detection, marginally faster)
uv run transcriber meeting.m4a -m large-v3 -d cuda --diarize -l en

# JSON output + custom output path
uv run transcriber meeting.mp3 -d cuda -f json -o ./transcripts/meeting
```

### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `-m, --model` | Model size: tiny, base, small, medium, large-v2, large-v3 | `base` |
| `-d, --device` | Compute device (cpu, cuda) | `cpu` |
| `-c, --compute-type` | Precision: float16, int8, float32, auto | `auto` |
| `-l, --language` | Language code, e.g. `en`, `pl` (auto-detect if omitted) | auto |
| `-f, --format` | Output format: md, json | `md` |
| `-o, --output` | Output path without extension | input filename |
| `-b, --batch-size` | Inference batch size | `16` |
| `--diarize` | Enable speaker diarization | off |
| `--hf-token` | HuggingFace token (overrides `HF_TOKEN` env var) | from `.env` |

### Supported audio formats

`.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.wma`, `.aac`, `.mp4`, `.webm`


## Development

Run `uv run just` to list all available commands.
Two commands cover everything before a commit:

```bash
uv run just check        # format + lint + type check + security + pre-commit hooks
uv run just test         # run the test suite with coverage
```

### Other

| Command | Description |
|---------|-------------|
| `uv run just commit-files` | Create a conventional commit interactively |
| `uv run just clean` | Remove all build/cache/coverage artifacts |
