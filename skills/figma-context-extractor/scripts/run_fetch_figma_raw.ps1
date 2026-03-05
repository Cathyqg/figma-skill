param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetScript = Join-Path $scriptDir "fetch_figma_raw.py"

if (-not (Test-Path $targetScript)) {
    Write-Error "Missing script: $targetScript"
    exit 1
}

$candidates = @(
    @{ Exe = "py"; Prefix = @("-3") },
    @{ Exe = "py"; Prefix = @() },
    @{ Exe = "python3"; Prefix = @() },
    @{ Exe = "python"; Prefix = @() }
)

foreach ($candidate in $candidates) {
    $exe = $candidate.Exe
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
        continue
    }

    $args = @()
    $args += $candidate.Prefix
    $args += @($targetScript)
    $args += $ScriptArgs

    & $exe @args
    exit $LASTEXITCODE
}

Write-Error "No Python launcher found. Install Python or ensure one of these is available: py, python3, python."
exit 1
