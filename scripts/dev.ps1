$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"

Write-Host "SF3D Web Tool local development helper"
Write-Host "1. Start the backend from $BackendPath"
Write-Host "   uvicorn app.main:app --reload --port 8000"
Write-Host "2. Start the frontend from $FrontendPath"
Write-Host "   npm run dev"
Write-Host "3. Replace the mock inference service before expecting real 3D outputs"
