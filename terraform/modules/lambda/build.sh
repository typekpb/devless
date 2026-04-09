#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Building Lambda functions..."

# Clean and create build directories
rm -rf builds
mkdir -p builds/webhook_handler builds/dlq_processor

# Copy Lambda code
cp -r ../../../lambda/webhook_handler/* builds/webhook_handler/
cp -r ../../../lambda/dlq_processor/* builds/dlq_processor/

# Install dependencies in venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r builds/webhook_handler/requirements.txt -t builds/webhook_handler/ --quiet
pip install -r builds/dlq_processor/requirements.txt -t builds/dlq_processor/ --quiet
deactivate

# Clean up venv
rm -rf .venv

echo "==> Lambda builds complete"
