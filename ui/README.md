# Transcriber UI

Minimal React + TypeScript + Vite front-end for uploading or recording audio
and submitting it for transcription.

## Development

```bash
npm install
npm run dev      # start dev server (proxies API to localhost:8000)
npm run test     # run unit tests
npm run lint     # lint with eslint
```

## Building for production

Run the build script from this directory:

```bash
# Linux / macOS
./build.sh

# Windows
build.bat
```

The build outputs static files to `../src/transcriber/server/static/` which
are served by the FastAPI server at `/ui`.
