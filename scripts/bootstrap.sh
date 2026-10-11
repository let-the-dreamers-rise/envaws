#!/usr/bin/env bash
# Installs the AWS CLI and SAM CLI into .venv-deploy when they aren't already on PATH.
# deploy.sh picks up .venv-deploy automatically.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if command -v aws >/dev/null 2>&1 && command -v sam >/dev/null 2>&1; then
  echo "aws $(aws --version 2>&1 | cut -d' ' -f1) and $(sam --version) already installed"
  exit 0
fi
python3 -m venv "$ROOT/.venv-deploy"
"$ROOT/.venv-deploy/bin/pip" install -q --upgrade pip
"$ROOT/.venv-deploy/bin/pip" install -q awscli aws-sam-cli
"$ROOT/.venv-deploy/bin/aws" --version
"$ROOT/.venv-deploy/bin/sam" --version
command -v zip >/dev/null 2>&1 || echo "WARNING: 'zip' is not installed; deploy.sh needs it for the frontend upload."
