---
name: pytest
description: >
  Enforce pytest conventions: test location, naming, fixtures, and assertion
  patterns. Trigger when writing or reviewing Python test files.
---

- Write tests in `tests/` directories co-located with source modules
- Use descriptive test function names: `test_<what>_<condition>_<expected>`
- Prefer fixtures over setup/teardown methods
- Use `pytest.raises` for exception assertions
