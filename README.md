# Transcriber

Local audio transcription tool powered by **WhisperX**. Transcribes meeting recordings with word-level timestamps and optional speaker diarization. Everything runs locally — no data leaves your machine.

## Features

- **WhisperX-powered** transcription with automatic language detection
- **Speaker diarization** — identifies who said what (optional, requires free HuggingFace token; word-level alignment runs automatically when enabled)
- **Multiple interfaces** — CLI for files, HTTP/WebSocket server for real-time apps, importable client library for GUI apps and scripts
- **Markdown & JSON output** — clean transcript ready to pass to an LLM for summarization
- **Configurable models** — tiny through large-v3, CPU or CUDA
- **Cache management** — pre-download models and check cache status for fully offline operation
- **`.env` configuration** — all settings configurable via environment variables


## Architecture

The code is split into four sub-packages. The boundary rule is simple: ML model calls stay in `pipeline/`, data movement stays in `io/`, shared types and config stay in `core/`, and everything the user directly interacts with stays in `cli/`. This means replacing WhisperX with a different backend only touches `pipeline/`.

### Sub-packages

| Package | What it contains | Key responsibility |
|---------|-----------------|-------------------|
| `core/` | Config dataclass, Pydantic result/segment models | Single source of truth for settings and data shapes shared across all other packages |
| `io/` | Audio loader, transcript writer | Format-level I/O with no model dependency — decodes audio, writes Markdown/JSON |
| `pipeline/` | Transcription orchestrator, alignment, diarization | All ML inference; owns the WhisperX and pyannote calls |
| `cli/` | Argument parser, Rich display, entry point, cache manager | User interface only; delegates everything to `pipeline/` and `io/` |
| `server/` | FastAPI app, routes, inference worker | HTTP/WebSocket server; single-GPU queue-based inference |
| `client/` | Microphone recorder, REST/WS sender | Start/stop recording API designed for GUI apps and scripts; no ML dependency |

### Processing pipeline

`TranscriptionPipeline` (in `pipeline/`) sequences the stages below. The Whisper model is loaded once on the first call and reused, so processing multiple files in one session is cheap.

1. **Audio decoding** (`io/`) — any supported container is decoded into a 16 kHz mono float32 array. This is the exact format WhisperX requires, so no conversion happens inside the model code.
2. **ASR transcription** (`pipeline/`) — WhisperX batch inference. Produces text segments with coarse sentence-level timestamps.
3. **Speaker diarization** (`pipeline/`, optional) — when enabled, first runs a forced-alignment pass (wav2vec2-based) to refine coarse timestamps to individual words, then pyannote detects speaker-turn boundaries and WhisperX assigns a speaker label to each word. A custom re-segmentation pass splits any segment that crosses a speaker boundary, so every output segment belongs to exactly one speaker. WhisperX's default majority-vote assignment does not do this split. If diarization fails for any reason, the pipeline falls back to the undiarized transcript rather than crashing.
4. **Output rendering** (`io/`) — the typed result is serialised to Markdown or JSON. Speaker turns are grouped into labelled blocks with timestamps, ready to paste into an LLM.


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
git clone https://github.com/galuszkm/transcriber.git
cd transcriber

# CLI transcription (includes ML engine)
uv sync --extra cli

# HTTP/WebSocket server (includes ML engine)
uv sync --extra server

# Microphone recording client (lightweight, no ML)
uv sync --extra client

# Everything (recommended)
uv sync --all-extras

# Dev tools + git hooks
uv run just install
```


## Configuration

All configuration is managed through `.env` file in the project root. The app loads it automatically via pydantic-settings. CLI arguments always override `.env` values.

### `.env` reference

```bash
# --- Shared settings (used by all commands) ---

# HuggingFace token (required only for speaker diarization)
HF_TOKEN=hf_your_token_here

# Whisper model size (default: large-v3)
MODEL=large-v3

# Compute device: cpu or cuda
DEVICE=cuda

# Enable speaker diarization (default: false)
DIARIZE=false

# Comma-separated language codes for cache pre-download (default: all)
# Only used by trans-cache; inference always auto-detects.
LANGUAGE=en,pl,de

# Override default cache directory (default: <cwd>/.cache)
CACHE_DIR=D:\models\cache
```

### Cache directory layout

All models and data are stored under a single cache root (default `.cache/`):

```
.cache/
├── huggingface/          # HuggingFace model weights
│   ├── hub/              # Whisper CTranslate2 + wav2vec2 alignment models
│   └── datasets/
├── torch/                # PyTorch hub models (torchaudio alignment models)
│   └── hub/checkpoints/
├── nltk/                 # NLTK tokenizer data
│   └── tokenizers/punkt_tab/
└── whisperx/             # Diarization cache (pyannote)
```

### Getting a HuggingFace token (for speaker diarization)

Diarization models are **free and MIT-licensed**, but gated (accept terms once):

1. Create a free account at [huggingface.co](https://huggingface.co/join)
2. Create a **Read** token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
3. Visit [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) and click **"Agree and access repository"**
4. Add the token to `.env`

Models are downloaded once on first use and cached locally. Fully offline after that.


## Cache management

Pre-download all models for fully offline operation. Reads defaults from `.env` (`MODEL`, `LANGUAGE`, `DEVICE`, `DIARIZE`) — CLI flags override. When no languages are specified, **all** languages with alignment models are cached.

```bash
# Download models using .env defaults (all languages)
uv run trans-cache

# Check what's already cached (no downloads)
uv run trans-cache --check

# Download specific models and languages
uv run trans-cache --models base large-v3 --languages en pl de zh

# Cache everything: all models, all languages, diarization
uv run trans-cache --all

# Include diarization models (requires HF_TOKEN in .env)
uv run trans-cache --diarize

# Custom cache directory
uv run trans-cache --cache-dir D:\models\cache
```

### Cache CLI options

| Flag | Description | Default (from `.env`) |
|------|-------------|---------|
| `--models SIZE [...]` | Whisper model sizes | `MODEL` or `large-v3` |
| `--languages LANG [...]` | ISO language codes for alignment | `LANGUAGE` or all available |
| `--device cpu\|cuda` | Device for model loading | `DEVICE` or `cpu` |
| `--diarize` | Also download diarization models | `DIARIZE` or `false` |
| `--all` | Cache all models, all languages, diarization | — |
| `--cache-dir PATH` | Override cache directory | `CACHE_DIR` or `.cache` |
| `--check` | Report cache status, download nothing | — |

### `--check` output example

```
  ✓ NLTK punkt_tab

  ✓ Whisper large-v3  (Systran/faster-whisper-large-v3)

  ✓ align en  (WAV2VEC2_ASR_BASE_960H, torchaudio)
  ✓ align pl  (jonatasgrosman/wav2vec2-large-xlsr-53-polish)
  ✓ align de  (VOXPOPULI_ASR_BASE_10K_DE, torchaudio)
  ✗ align zh  (jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn)
```


## CLI usage

```bash
# GPU with large model (default)
uv run trans-cli recording.wav

# CPU with smaller model
uv run trans-cli recording.mp3 -m base -d cpu

# With speaker detection
uv run trans-cli meeting.mp3 --diarize

# JSON output + custom output path
uv run trans-cli meeting.mp3 -f json -o ./transcripts/meeting
```

### CLI options

| Flag | Description | Default |
|------|-------------|---------|
| `-m, --model` | Model size: tiny, base, small, medium, large-v2, large-v3 | `large-v3` |
| `-d, --device` | Compute device (cpu, cuda) | `cuda` |
| `-c, --compute-type` | Precision: float16, int8, float32, auto | `auto` |
| `-f, --format` | Output format: md, json | `md` |
| `-o, --output` | Output path without extension | input filename |
| `-b, --batch-size` | Inference batch size | `16` |
| `--diarize` | Enable speaker diarization | off |
| `--hf-token` | HuggingFace token (overrides `HF_TOKEN` env var) | from `.env` |
| `--cache-dir` | Cache directory | `CACHE_DIR` or `.cache` |

### Supported audio formats

`.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.wma`, `.aac`, `.mp4`, `.webm`

### Model sizes

| Model | Parameters | VRAM | Relative speed | Best for |
|-------|-----------|------|----------------|----------|
| `tiny` | 39M | ~1 GB | fastest | Quick tests |
| `base` | 74M | ~1 GB | fast | Development, English-only |
| `small` | 244M | ~2 GB | moderate | Good balance |
| `medium` | 769M | ~5 GB | slow | Better multilingual |
| `large-v2` | 1550M | ~10 GB | slowest | High accuracy |
| `large-v3` | 1550M | ~10 GB | slowest | **Best accuracy**, especially non-English |


## Server

HTTP/WebSocket server for integrating transcription into other applications. Runs a single-GPU inference worker with a FIFO queue.

```bash
# Start server (defaults: cuda, large-v3, port 8000)
uv run trans-server

# Custom port and model
uv run trans-server --port 9876 -m base

# CPU mode
uv run trans-server -d cpu --port 9876
```

### Server options

| Flag | Description | Default |
|------|-------------|---------|
| `--host` | Bind address | `127.0.0.1` |
| `--port` | Port number | `8000` |
| `-m, --model` | Whisper model size | `large-v3` |
| `-d, --device` | Compute device | `cuda` |
| `-c, --compute-type` | Precision | `auto` |
| `-b, --batch-size` | Batch size | `16` |
| `--hf-token` | HuggingFace token | from `.env` |
| `--cache-dir` | Cache directory | `.cache` |

### API endpoints

#### Health check

```
GET /health
```

Returns model status, device, and queue size.

#### Transcription (synchronous)

Multiple input methods, all returning the same `TranscribeResponse`:

| Endpoint | Content-Type | Input |
|----------|-------------|-------|
| `POST /transcribe` | `multipart/form-data` | `file` field (audio file) or `audio_base64` field |
| `POST /transcribe/json` | `application/json` | `{"audio_base64": "...", "diarize": false}` |
| `POST /transcribe/raw` | `application/octet-stream` | Raw audio bytes |

All accept `?diarize=true` query parameter (or `diarize` field in JSON body).

**Response:**

```json
{
  "transcript": "Full text...",
  "segments": [
    {"start": 0.5, "end": 2.1, "text": "Hello everyone.", "speaker": "SPEAKER_00"}
  ],
  "language": "en",
  "duration": 45.2,
  "timings": {"model_load": 0.01, "transcribe": 3.2}
}
```

#### Transcription (SSE streaming)

Same input methods with `/stream` suffix — returns Server-Sent Events with progress updates:

| Endpoint | Input |
|----------|-------|
| `POST /transcribe/stream` | Multipart or base64 form |
| `POST /transcribe/json/stream` | JSON body |
| `POST /transcribe/raw/stream` | Raw bytes |

**SSE events:**

```
event: progress
data: {"stage": "transcribe", "message": "Transcribing speech"}

event: complete
data: {"transcript": "...", "segments": [...], ...}
```

#### WebSocket

```
WS /ws/transcribe?diarize=true
```

Send binary audio frame → receive JSON response. Connection stays open for multiple exchanges.

### Client library

A lightweight, importable library for recording audio and sending it to the server. No ML dependencies — install with the `client` extra:

```bash
uv sync --extra client
```

The recording API is **non-blocking** and designed for GUI apps: `start_recording` returns immediately while audio is captured in a background thread. Call `stop_recording` whenever the user is done, regardless of how much time has passed.

For sending audio to the server, prefer `transcribe_sse` over `transcribe_rest` for long recordings — it streams progress events back while the pipeline runs, so the HTTP connection never idles long enough to time out.

#### GUI integration (e.g. PySide6 button handler)

```python
from transcriber.client import (
    RecordingError,
    is_recording,
    list_devices,
    start_recording,
    stop_recording,
    transcribe_rest,
)

# List available input devices
print(list_devices())

def on_record_button_clicked():
    if is_recording():
        wav = stop_recording()          # returns WAV bytes immediately
        result = transcribe_rest(wav)   # blocks until server responds
        print(result["transcript"])
    else:
        start_recording(device=2)       # returns immediately, records in background
```

#### Script usage (blocking until done)

```python
import time
from transcriber.client import start_recording, stop_recording, transcribe_sse

start_recording(max_duration=60.0)  # safety cap; stops automatically at 60 s
time.sleep(30)                       # record for 30 seconds
wav = stop_recording()

result = transcribe_sse(
    wav,
    url="http://localhost:8000",
    diarize=True,
    on_progress=lambda stage, msg: print(f"[{stage}] {msg}"),
)
print(result["transcript"])
```

#### API reference

| Symbol | Description |
|--------|-------------|
| `start_recording(*, device, sample_rate, channels, max_duration)` | Begin capturing; returns immediately |
| `stop_recording()` | Stop and return in-memory WAV bytes |
| `is_recording()` | `True` if a session is active |
| `list_devices()` | Human-readable list of available audio devices |
| `transcribe_rest(wav_bytes, *, url, diarize, timeout)` | POST to `/transcribe`; returns parsed result dict |
| `transcribe_sse(wav_bytes, *, url, diarize, timeout, on_progress)` | Stream via SSE; calls `on_progress(stage, message)` for each progress event; returns parsed result dict — prefer over REST for large files |
| `transcribe_ws(wav_bytes, *, url, diarize)` | Send over WebSocket; returns parsed result dict |
| `RecordingError` | Raised on invalid operations (already recording, not recording) |


## Development

Run `uv run just` to list all available commands.
Two commands cover everything before a commit:

```bash
uv run just check        # format + lint + type check + security + pre-commit hooks
uv run just test         # run the test suite with coverage
```

### Task reference

| Command | Description |
|---------|-------------|
| `uv run just install` | Install all deps + git hooks |
| `uv run just check` | Run all checks (format, lint, types, security, hooks, audit) |
| `uv run just test` | Run tests with coverage |
| `uv run just format` | Auto-format code (imports + source) |
| `uv run just clean` | Remove build/cache/coverage artifacts |
| `uv run just commit-files` | Create a conventional commit interactively |
