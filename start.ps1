$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting ResumeCraft..." -ForegroundColor Cyan

$BackendCmd = "Set-Location '$Root\backend'; .\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCmd

$NextBin = "$Root\frontend\node_modules\.bin\next.cmd"
if (Test-Path $NextBin) {
    $FrontendCmd = "Set-Location '$Root\frontend'; `$env:NODE_OPTIONS='--dns-result-order=ipv4first'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCmd
    Write-Host "Next.js UI:   http://localhost:3000" -ForegroundColor Green
} else {
    Write-Host "Built-in UI:  http://127.0.0.1:8000 (ready immediately without node_modules)" -ForegroundColor Green
}

Write-Host "Swagger Docs: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
