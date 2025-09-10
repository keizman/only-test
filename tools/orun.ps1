Param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

# Run a Python command inside the 'orun' conda environment.
# Usage: ./tools/orun.ps1 -- only_test/examples/mcp_llm_workflow_demo.py --requirement "..." ...

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Error "Conda is not available in PATH. Please install Anaconda/Miniconda."
    exit 1
}

conda run -n orun python @Args

