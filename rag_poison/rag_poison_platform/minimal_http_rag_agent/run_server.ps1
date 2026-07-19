# Start minimal_http_rag_agent on port 18100 (isolated venv).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -q -r requirements.txt

$env:PYTHONPATH = $Root
# Parent platform .env is loaded inside app.py

Write-Host "Starting minimal_http_rag_agent on http://127.0.0.1:18100"
Write-Host "If you changed app.py, stop any old process on port 18100 before starting."
.\.venv\Scripts\uvicorn.exe app:app --host 127.0.0.1 --port 18100
