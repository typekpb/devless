---
name: testing-patterns
description: >
  Enforce general testing patterns: coverage of happy/error/boundary paths,
  minimal mocking, deterministic tests, and preference for integration tests.
  Trigger when writing or reviewing any test code.
---

- Test the happy path, error paths, and boundary conditions
- Avoid mocking unless testing I/O or external services
- Keep tests deterministic and independent of each other
- Prefer integration tests over unit tests for pipeline stages
