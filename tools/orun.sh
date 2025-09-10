#!/usr/bin/env bash
set -euo pipefail

# Run a Python command inside the 'orun' conda environment.
# Usage: tools/orun.sh only_test/examples/mcp_llm_workflow_demo.py --requirement "..." ...

if ! command -v conda >/dev/null 2>&1; then
  echo "Conda is not available in PATH. Please install Anaconda/Miniconda." >&2
  exit 1
fi

conda run -n orun python "$@"

