$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$patterns = @(
    "BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY",
    "AKIA[0-9A-Z]{16}",
    "gh[pousr]_[A-Za-z0-9_]{20,}",
    "xox[baprs]-[A-Za-z0-9-]{20,}",
    "DATABASE_URL\s*=\s*postgres(?:ql)?://(?!opendq:opendq@localhost)"
)
$excluded = @(".git", "node_modules", ".next", ".venv", "pipeline/.venv")
$hits = @()
foreach ($pattern in $patterns) {
    $result = rg --hidden --no-heading --line-number --glob "!.git/**" --glob "!node_modules/**" --glob "!.next/**" --glob "!pipeline/.venv/**" -P $pattern $repo 2>$null
    if ($LASTEXITCODE -eq 0) { $hits += $result }
}
if ($hits.Count -gt 0) {
    Write-Error "Potential secret pattern detected. Review locally without printing secret contents."
    exit 1
}
Write-Output "SECRET_SCAN=PASS (conservative patterns; no matching secret material found)"
exit 0
