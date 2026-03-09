# run all UI checks and tests
[group("ui")]
ui: ui-install ui-lint ui-typecheck ui-test

# install UI dependencies
[group("ui")]
ui-install:
    npm --prefix ui install

# lint UI code
[group("ui")]
ui-lint:
    npm --prefix ui run lint

# check TypeScript types
[group("ui")]
ui-typecheck:
    npm --prefix ui run typecheck

# run UI tests
[group("ui")]
ui-test:
    npm --prefix ui run test

# build UI (outputs to src/transcriber/server/static/)
[group("ui")]
ui-build: ui-install ui-typecheck
    npm --prefix ui run build
