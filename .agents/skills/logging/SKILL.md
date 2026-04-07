---
name: logging
description: >
  Enforce structured logging conventions: JSON format, consistent fields, and
  appropriate log levels. Trigger when adding or modifying log statements.
---

- Emit structured JSON logs with `level`, `message`, and `timestamp` fields
- Include relevant context (issue number, repo, stage) in every log entry
- Use `INFO` for normal progress, `WARNING` for recoverable issues, `ERROR` for failures
