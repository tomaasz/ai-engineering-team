# ==============================================================================
# AI Engineering Team - One-Command Project Setup & Onboarding Script (PowerShell)
# Automatyczny skrypt instalacji, konfiguracji i weryfikacji projektów
# ==============================================================================
[CmdletBinding()]
param(
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ai-team -ErrorAction SilentlyContinue)) {
    Write-Host "==> ai-team CLI nie jest zainstalowane. Rozpoczynam instalacje..." -ForegroundColor Cyan
    pip install --user --upgrade "git+https://github.com/tomaasz/ai-engineering-team.git"
}

& ai-team onboard @RemainingArgs
