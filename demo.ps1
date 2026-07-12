# 平台端到端演示脚本
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "`n========== 1/4 离线模块 (defense + multiagent) ==========" -ForegroundColor Cyan
python platform\run_quick_eval.py --offline-only --modules defense,multiagent

Write-Host "`n========== 2/4 Prompt 投毒 (需 DEEPSEEK_API_KEY) ==========" -ForegroundColor Cyan
python platform\run_module.py prompt
if ($LASTEXITCODE -ne 0) { Write-Host "[warn] prompt module skipped or failed (check API key)" -ForegroundColor Yellow }

Write-Host "`n========== 3/4 导入最新 Prompt 结果到后端 ==========" -ForegroundColor Cyan
$latest = Get-ChildItem "prompt_poison\mytest\results\deepseek_direct_prompt_injection_*.json" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latest) {
    python platform\aggregate_results.py $latest.FullName --post
}

Write-Host "`n========== 4/4 API 健康检查 ==========" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod "http://127.0.0.1:8100/health"
    $exps = Invoke-RestMethod "http://127.0.0.1:8100/api/experiments"
    Write-Host "Server OK | rules=$($health.rule_count) | experiments=$($exps.data.Count)"
} catch {
    Write-Host "Backend not running. Start with: cd defense_engine\defense_engine; python -m uvicorn server:app --port 8100"
}

Write-Host "`nDemo complete." -ForegroundColor Green
