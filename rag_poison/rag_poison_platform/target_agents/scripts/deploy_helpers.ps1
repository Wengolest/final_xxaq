# Helper: sync LLM keys from rag_poison_platform .env into target agent .env (not committed).
param(
    [Parameter(Mandatory = $true)][string]$AgentDir,
    [string]$PlatformEnv = "D:\AI\rag_poison_exp\rag_poison_platform\.env",
    [string]$AgentId = ""
)

$map = @{}
Get-Content $PlatformEnv | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $map[$matches[1].Trim()] = $matches[2].Trim()
    }
}

$key = $map['DEEPSEEK_API_KEY']
$base = $map['DEEPSEEK_BASE_URL']
if (-not $base) { $base = 'https://api.deepseek.com' }
$model = $map['DEEPSEEK_MODEL']
if (-not $model) { $model = 'deepseek-chat' }

if (-not $key) {
    Write-Host "DEEPSEEK_API_KEY missing in $PlatformEnv; wrote mock-only .env"
    $lines = @("# mock backend: no LLM keys")
} else {
    $masked = if ($key.Length -gt 4) { "ds-****" + $key.Substring($key.Length - 4) } else { "****" }
    if ($AgentId -eq 'enterprise-rag-chatbot' -or $AgentDir -match 'enterprise-rag-chatbot') {
        $lines = @(
            "VLLM_API_KEY=$key",
            "VLLM_BASE_URL=$base",
            "VLLM_MODEL_NAME=$model",
            "LLM_PROVIDER=vllm",
            "VECTOR_DB_TYPE=chroma",
            "USE_UNIFIED_PROVIDER=false"
        )
    } elseif ($AgentId -eq 'agent-service-toolkit' -or $AgentDir -match 'agent-service-toolkit') {
        $lines = @(
            "DEEPSEEK_API_KEY=$key",
            "OPENAI_API_KEY=$key",
            "OPENAI_API_BASE=$base",
            "DATABASE_TYPE=sqlite",
            "DEFAULT_MODEL=deepseek-chat"
        )
    } elseif ($AgentId -eq 'rag-fastapi-chatbot' -or $AgentDir -match 'rag-fastapi-chatbot') {
        $lines = @(
            'DATABASE_URL_ASYNCPG_DRIVER=postgresql+asyncpg://poison_test:poison_test_pass@127.0.0.1:15433/poison_test_db',
            'DATABASE_URL_PSYCOPG_DRIVER=postgresql+psycopg://poison_test:poison_test_pass@127.0.0.1:15433/poison_test_db',
            'PSYCOPG_CONNECT=postgresql://poison_test:poison_test_pass@127.0.0.1:15433/poison_test_db',
            'MINIO_URL=127.0.0.1:19000',
            'MINIO_ACCESS_KEY=poisonminio',
            'MINIO_SECRET_KEY=poisonminiosecret',
            'BUCKET_NAME=document-for-rag',
            'SALT=poison_test_salt',
            'ALGORITHM=HS256',
            'ACCESS_TOKEN_EXPIRE_MINUTES=60',
            'JTI_EXPIRY_SECOND=3600',
            'REFRESH_TOKEN_EXPIRE_DAYS=7',
            'SECRET_KEY=poison_test_secret',
            'POSTGRES_USER=poison_test',
            'POSTGRES_PASSWORD=poison_test_pass',
            'POSTGRES_DB=poison_test_db',
            'REDIS_URL=redis://127.0.0.1:16379',
            'BROKER_URL=redis://127.0.0.1:16379/0',
            'BACKEND_URL=redis://127.0.0.1:16379/1',
            'EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2',
            'HF_TOKEN=hf_poison_test',
            'LLM_MODEL=qwen2.5:0.5b',
            'OLLAMA_HOST=http://127.0.0.1:11435',
            'DOMAIN_NAME=localhost',
            'VERSION=api/v1',
            'MAIL_USERNAME=poison@test.local',
            'MAIL_PASSWORD=poison_test',
            'MAIL_FROM=poison@test.local',
            'MAIL_SERVER=localhost'
        )
    } elseif ($AgentId -eq 'ai-chatkit' -or $AgentDir -match 'ai-chatkit') {
        $lines = @(
            "OPENAI_API_KEY=$key",
            "OPENAI_API_BASE=$base",
            "MODEL=$model",
            "DATABASE_URL=sqlite+aiosqlite:///./poison_test.db"
        )
    } elseif ($AgentId -eq 'tech-trends-chatbot' -or $AgentDir -match 'tech-trends-chatbot') {
        $lines = @(
            "OPENAI_API_KEY=$key",
            "MODEL=$model",
            "REDIS_HOST=127.0.0.1",
            "REDIS_PORT=6380",
            "DOCS_DIR=data/docs",
            "EXPORT_DIR=data/export"
        )
    } else {
        $lines = @(
            "DEEPSEEK_API_KEY=$key",
            "DEEPSEEK_BASE_URL=$base",
            "DEEPSEEK_MODEL=$model",
            "OPENAI_API_KEY=$key",
            "OPENAI_API_BASE=$base",
            "OPENAI_BASE_URL=$base",
            "OPENAI_MODEL=$model",
            "BASE_URL=$base",
            "MODEL=$model",
            "MODEL_NAME=$model",
            "LLM_MODEL=$model",
            "VLLM_API_KEY=$key",
            "VLLM_BASE_URL=$base",
            "VLLM_MODEL_NAME=$model"
        )
    }
    Write-Host "Wrote DeepSeek-compat .env (key masked: $masked)"
}

$out = Join-Path $AgentDir '.env'
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllLines($out, $lines, $utf8NoBom)
Write-Host "Wrote $out"
