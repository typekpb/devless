---
name: error-handling
description: >
  Enforce error handling best practices: explicit exception handling, contextual
  logging, error propagation, and custom exception types. Trigger when writing
  code that deals with failures, I/O, or external services.
---

- Always handle exceptions explicitly; never swallow errors silently
- Log errors with sufficient context to diagnose the issue
- Propagate errors to the caller when the current layer cannot handle them
- Use custom exception types to distinguish error categories
