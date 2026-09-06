$ErrorActionPreference = "Stop"
$env:APP_ENV = "demo"
$env:BENCHMARK_DATABASE_URL = "postgresql://opendq:opendq@localhost:5432/opendq_demo"
try {
    & "$PSScriptRoot/../pipeline/.venv/Scripts/python.exe" -m opendq benchmark --runs 5
    if ($LASTEXITCODE -ne 0) { throw "benchmark failed with exit code $LASTEXITCODE" }
}
finally {
    Remove-Item Env:APP_ENV, Env:BENCHMARK_DATABASE_URL -ErrorAction SilentlyContinue
}
