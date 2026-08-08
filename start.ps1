# ACIS Docker 一键启动脚本（Windows / PowerShell）
# 用法:
#   .\start.ps1            启动（构建 + 起服务 + 等待健康）
#   .\start.ps1 import     可选: 导入真实 AgriKG 图谱到 Neo4j
#   .\start.ps1 status     查看服务状态
#   .\start.ps1 logs       跟踪 API 日志
#   .\start.ps1 stop       停止（保留数据卷）
# 可选: 设置 $env:DEEPSEEK_API_KEY='sk-...' 后启动, 启用 LLM Judge/Critic

param(
    [ValidateSet("start", "import", "status", "logs", "stop", "help")]
    [string]$Command = "start"
)

$ErrorActionPreference = "Stop"

# Windows 系统代理（如 Clash 127.0.0.1:7892）会劫持 httpx 对 localhost 的请求
# 导致 Docker 本地服务（Qdrant 6333 等）返回 502；显式绕过本地地址。
$env:NO_PROXY = "localhost,127.0.0.1"
$env:no_proxy = $env:NO_PROXY

function Require-Docker {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ACIS] Docker 未运行。请先启动 Docker Desktop 后重试。" -ForegroundColor Red
        exit 1
    }
}

function Wait-Healthy {
    Write-Host "[ACIS] 等待 API 就绪 (http://localhost:8000/health) ..." -ForegroundColor Yellow
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 2
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) {
                Write-Host "[ACIS] API 就绪: $($r.Content)" -ForegroundColor Green
                return
            }
        } catch {
            # retry
        }
    }
    Write-Host "[ACIS] API 在 60s 内未就绪, 查看日志: .\start.ps1 logs" -ForegroundColor Red
    exit 1
}

function Show-Hints {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  ACIS 已启动" -ForegroundColor Cyan
    Write-Host "  API:        http://localhost:8000   (GET /health, POST /diagnose)" -ForegroundColor Cyan
    Write-Host "  Neo4j 控制台: http://localhost:17474 (neo4j / agriai2026)" -ForegroundColor Cyan
    Write-Host "  Qdrant:     http://localhost:6333" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "提示:" -ForegroundColor Green
    Write-Host "  - 启用 LLM Judge/Critic: 启动前设置 \$env:DEEPSEEK_API_KEY='sk-...'"
    Write-Host "  - 导入真实 AgriKG 图谱:  .\start.ps1 import"
    Write-Host "  - 停止:                .\start.ps1 stop"
}

switch ($Command) {
    "start" {
        Require-Docker
        docker compose up -d --build
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Wait-Healthy
        Show-Hints
    }
    "import" {
        Require-Docker
        if (-not (Test-Path "data/Agriculture_KnowledgeGraph-master")) {
            Write-Host "[ACIS] 未找到 data/Agriculture_KnowledgeGraph-master, 跳过导入。" -ForegroundColor Yellow
            Write-Host "       将 AgriKG 数据解压到该目录后重新运行 .\start.ps1 import" -ForegroundColor Yellow
            exit 0
        }
        docker compose exec api python scripts/import_agrikg.py --yes
    }
    "status" { Require-Docker; docker compose ps }
    "logs"   { Require-Docker; docker compose logs -f api }
    "stop"   {
        Require-Docker
        docker compose down
        Write-Host "[ACIS] 已停止（数据卷保留）。如需清空数据: docker compose down -v" -ForegroundColor Yellow
    }
    "help"   { Get-Help $PSCommandPath }
}
