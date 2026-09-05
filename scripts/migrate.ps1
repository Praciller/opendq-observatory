$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Join-Path $repo "pipeline\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Create pipeline/.venv before running migrations." }
& $python -m opendq migrate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

