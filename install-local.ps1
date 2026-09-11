$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
py -m pip install --user pipx
py -m pipx ensurepath
py -m pipx install --force $Repo
Write-Host "Zainstalowano ai-team. Otwórz nowy terminal i uruchom: ai-team --help"
