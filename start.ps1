# ================================================================
# 一键启动: defense_proxy + 防御后端 + 前端
#
# 启动后:
#   defense_proxy :8200  — OpenAI 兼容代理 (攻击模块 → 防御 → LLM)
#   后端 API  :8100/docs — FastAPI Swagger
#   前端       :5173      — React Dashboard
# ================================================================
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

# ---- 1. 加载 .env / .env.proxy ----
if (-not (Test-Path "$Root\.env")) {
    if (Test-Path "$Root\.env.example") {
        Copy-Item "$Root\.env.example" "$Root\.env"
        Write-Host "[info] Created .env from .env.example — edit DEEPSEEK_API_KEY before real-LLM runs"
    }
}

# 若存在 .env.proxy 则加载环境变量 (使所有模块自动指向 defense_proxy)
if (Test-Path "$Root\.env.proxy") {
    Write-Host "[info] Loading .env.proxy → all poison modules will route through defense_proxy :8200"
    Get-Content "$Root\.env.proxy" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $k, $v = $line.Split("=", 2)
            [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), "Process")
        }
    }
}

# ---- 2. 启动 defense_proxy (OpenAI-compatible, port 8200) ----
Write-Host "Starting defense_proxy on :8200 ..."
$ProxyScript = "$Root\defense_engine\defense_engine\defense_proxy.py"
if (Test-Path $ProxyScript) {
    $ProxyDir = Split-Path -Parent $ProxyScript
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProxyDir'; python -m uvicorn defense_proxy:app --host 127.0.0.1 --port 8200"
    Write-Host "  defense_proxy starting on http://127.0.0.1:8200"
} else {
    Write-Host "  [WARN] defense_proxy.py not found at $ProxyScript — skipping"
}

# ---- 3. 启动防御引擎后端 (port 8100) ----
Write-Host "Starting defense_engine on :8100 ..."
$DefenseDir = "$Root\defense_engine\defense_engine"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$DefenseDir'; python -m uvicorn server:app --host 127.0.0.1 --port 8100"

Start-Sleep -Seconds 3

# ---- 4. 启动前端 (port 5173, proxy /api → :8100) ----
Write-Host "Starting front_web on :5173 ..."
$FrontDir = "$Root\front_web\web"
if (Test-Path "$FrontDir\package.json") {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$FrontDir'; if (-not (Test-Path node_modules)) { npm install }; npm run dev"
} else {
    Write-Host "  [WARN] $FrontDir\package.json not found"
}

# ---- 完成 ----
Write-Host ""
Write-Host "Done. Services:"
Write-Host "  defense_proxy : http://127.0.0.1:8200  (transparent firewall)"
Write-Host "  backend API   : http://127.0.0.1:8100/docs"
Write-Host "  frontend      : http://127.0.0.1:5173"
Write-Host ""
Write-Host "Run an attack module with proxy: `$env:DEEPSEEK_BASE_URL='http://localhost:8200/v1'"
