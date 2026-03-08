# run all UI checks and tests
[group("ui")]
ui: ui-install ui-lint ui-typecheck ui-test

# install UI dependencies
[group("ui")]
ui-install:
    cd ui && npm ci --prefer-offline 2>/dev/null || cd ui && npm install

# lint UI code
[group("ui")]
ui-lint:
    cd ui && npm run lint

# check TypeScript types
[group("ui")]
ui-typecheck:
    cd ui && npx tsc -b --noEmit

# run UI tests
[group("ui")]
ui-test:
    cd ui && npm run test

# build UI (outputs to src/transcriber/server/static/)
[group("ui")]
ui-build: ui-install ui-typecheck
    cd ui && npm run build
