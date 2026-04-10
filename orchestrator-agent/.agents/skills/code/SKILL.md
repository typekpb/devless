---
name: code
description: Code operations via Aider
---

# Code Operations

## Available Tools

### read_project_config
Read `.devless/config.yml` from the repository.
```
read_project_config()
```
Returns:
- `model`: LLM model for Aider (e.g., "bedrock/eu.anthropic.claude-sonnet-4-20250514-v1:0")
- `test_command`: Command to run tests (e.g., "pytest", "npm test")
- `max_iterations`: Max attempts for Aider to pass tests

### run_aider
Run Aider to make code changes.
```
run_aider(
    message="Implement feature X as described in the issue",
    test_command="pytest",
    max_iterations=10,
    model="bedrock/eu.anthropic.claude-sonnet-4-20250514-v1:0"
)
```
Returns:
- `success`: Whether changes were made and tests pass
- `needs_clarification`: Whether Aider needs more info
- `clarification_question`: The question if clarification needed
- `output`: Aider's output (truncated)

### list_files
List files in the repository.
```
list_files(path="src")
```

### read_file
Read a file's contents.
```
read_file(path="src/main.py")
```

## Using run_aider

Always:
1. Call `read_project_config` first to get settings
2. Pass the config values to `run_aider`
3. Include full issue context in the message

Message format for issues:
```
Issue #{number}: {title}

{body}

## Comments
{comments if any}

Please implement the requested changes. Run tests with: {test_command}
```

Message format for PR feedback:
```
PR #{number} received feedback:

{feedback}

Please address this feedback. Run tests with: {test_command}
```

## Handling Clarification

If `run_aider` returns `needs_clarification=True`:
1. Post a comment with the clarification question
2. Use 🤔 emoji
3. Stop processing (user will reply, triggering new event)
