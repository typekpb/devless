---
name: hypothesis
description: >
  Enforce property-based testing with Hypothesis: strategy usage, example counts,
  tagging conventions, and input filtering. Trigger when writing or reviewing
  property-based tests.
---

- Use `@given` decorator with appropriate strategies to generate inputs
- Run at least 100 examples per property (`settings(max_examples=100)`)
- Tag each property test with: `# Feature: <name>, Property <N>: <description>`
- Write smart generators that constrain inputs to the valid domain
- Use `assume()` to filter out invalid inputs rather than catching exceptions
