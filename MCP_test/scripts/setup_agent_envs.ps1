# Setup per-agent venv under agents/ (requires network)
$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AgentsRoot = Join-Path $Root "agents"
$Py = "python"

function Setup-AgentVenv {
    param([string]$Name, [string[]]$PipArgs)
    $Dir = Join-Path $AgentsRoot $Name
    if (-not (Test-Path $Dir)) {
        Write-Host "[SKIP] $Name - missing"
        return
    }
    $Venv = Join-Path $Dir "venv"
    Write-Host ""
    Write-Host "=== $Name ==="
    if (-not (Test-Path $Venv)) {
        & $Py -m venv $Venv
    }
    $pip = Join-Path $Venv "Scripts\pip.exe"
    & $pip install --upgrade pip -q
    foreach ($arg in $PipArgs) {
        Write-Host "  pip install $arg"
        & $pip install $arg
    }
    $readme = Join-Path $Dir "ENV_README.txt"
    "Agent: $Name`nActivate: .\venv\Scripts\Activate.ps1" | Out-File -FilePath $readme -Encoding utf8
}

$MainVenv = Join-Path $Root "venv"
if (-not (Test-Path $MainVenv)) {
    & $Py -m venv $MainVenv
}
& (Join-Path $MainVenv "Scripts\pip.exe") install -r (Join-Path $Root "requirements.txt") -q

$pa = Join-Path $AgentsRoot "pydantic-ai"
$sa = Join-Path $AgentsRoot "strands-agents"

Setup-AgentVenv "swarm" @("openai>=1.0", "git+https://github.com/openai/swarm.git")
Setup-AgentVenv "pydantic-ai" @("-e", $pa)
Setup-AgentVenv "crewai" @("crewai", "crewai-tools")
Setup-AgentVenv "langroid" @("langroid")
Setup-AgentVenv "browser-use" @("browser-use")
Setup-AgentVenv "strands-agents" @("-e", $sa)
Setup-AgentVenv "autogen" @("autogen-agentchat", 'autogen-ext[mcp,openai]', "mcp>=1.0")

Write-Host ""
Write-Host "Done. Run: .\venv\Scripts\python.exe run_mcp_poison.py"
