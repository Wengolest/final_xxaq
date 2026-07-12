# 启动防御后端 + 前端
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path "$Root\.env")) {
    if (Test-Path "$Root\.env.example") {
        Copy-Item "$Root\.env.example" "$Root\.env"
        Write-Host "[info] Created .env from .env.example — set DEEPSEEK_API_KEY for LLM modules"
    }
}

Write-Host "Starting defense_engine on :8100 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\defense_engine\defense_engine'; python -m uvicorn server:app --host 127.0.0.1 --port 8100"

Start-Sleep -Seconds 2

Write-Host "Starting front_web on :5173 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\front_web\web'; if (-not (Test-Path node_modules)) { npm install }; npm run dev"

Write-Host "Done. Backend: http://127.0.0.1:8100/docs  Frontend: http://127.0.0.1:5173"
