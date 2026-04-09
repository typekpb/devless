---
name: testing
description: Running tests from target repo configuration
---

# Testing

## Run Tests from Config
```bash
if [ -f .devless/config.yml ]; then
  TEST_CMD=$(grep "test_command:" .devless/config.yml | cut -d: -f2- | xargs)
  if [ -n "$TEST_CMD" ]; then
    eval "$TEST_CMD"
  fi
fi
```

## Common Test Commands
- Python: `pytest`
- Node.js: `npm test` or `npx vitest --run`
- Go: `go test ./...`
- Java: `mvn test`
- Rust: `cargo test`

## Test Before Pushing
Always run tests before pushing if `test_command` is configured in `.devless/config.yml`.
