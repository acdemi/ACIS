param(
    [ValidateSet("start", "stop")]
    [string]$Action = "start",
    [ValidateRange(1, 65535)]
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path.TrimEnd("\")
$BaseUrl = $null
$StatePath = $null
$ServerProcess = $null
$LaunchRecord = $null
$StdoutLog = $null
$StderrLog = $null

Add-Type -AssemblyName System.Net.Http -ErrorAction Stop

function Write-Info([string]$Message) {
    Write-Host "[ACIS] $Message" -ForegroundColor Cyan
}

function Write-WarningMessage([string]$Message) {
    Write-Host "[ACIS] $Message" -ForegroundColor Yellow
}

function Write-Failure([string]$Message) {
    Write-Host "[ACIS] 错误：$Message" -ForegroundColor Red
}

function Get-StatePath {
    $normalizedRoot = $Root.ToLowerInvariant()
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = [System.BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($normalizedRoot))).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
    $base = [Environment]::GetFolderPath("LocalApplicationData")
    if ([string]::IsNullOrWhiteSpace($base)) {
        $base = [System.IO.Path]::GetTempPath()
    }
    $directory = Join-Path $base "ACIS\local-launcher"
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    return (Join-Path $directory "$hash.json")
}

function Get-PortValue {
    if ($Port -gt 0) {
        return $Port
    }
    $value = $env:ACIS_LOCAL_PORT
    if ([string]::IsNullOrWhiteSpace($value)) {
        $value = $env:ACIS_API_PORT
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        return 8000
    }
    $parsed = 0
    if (-not [int]::TryParse($value, [ref]$parsed) -or $parsed -lt 1 -or $parsed -gt 65535) {
        throw "ACIS_LOCAL_PORT / ACIS_API_PORT 必须是 1–65535 的端口号。"
    }
    return $parsed
}

function Get-PythonPath {
    $projectPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $projectPython -PathType Leaf) {
        return $projectPython
    }
    $systemPython = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($systemPython) {
        return $systemPython.Source
    }
    throw "没有找到 Python。请先安装 Python 3.11+ 或准备项目虚拟环境 .venv；启动器不会自动创建或覆盖虚拟环境。"
}

function Get-ProcessIdentity($Record) {
    if (-not $Record -or [int]$Record.pid -lt 1 -or [int]$Record.port -lt 1 -or [int]$Record.port -gt 65535) {
        return $null
    }
    try {
        $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $([int]$Record.pid)" -ErrorAction Stop
        if (-not $process -or -not $process.ExecutablePath -or -not $process.CommandLine) {
            return $null
        }
        $expectedExecutable = [System.IO.Path]::GetFullPath([string]$Record.python).TrimEnd("\")
        $actualExecutable = [System.IO.Path]::GetFullPath([string]$process.ExecutablePath).TrimEnd("\")
        if (-not $actualExecutable.Equals($expectedExecutable, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $null
        }
        $expectedStart = [DateTimeOffset]::Parse([string]$Record.started_utc).UtcDateTime
        $actualStart = ([datetime]$process.CreationDate).ToUniversalTime()
        if ([Math]::Abs(($actualStart - $expectedStart).TotalSeconds) -gt 2) {
            return $null
        }
        $commandLine = ([string]$process.CommandLine).Replace('"', "")
        $appDirectoryPattern = "(?i)--app-dir\s+$([regex]::Escape($Root))(?:\s|$)"
        $portPattern = "(?i)--port\s+$([int]$Record.port)(?:\s|$)"
        if ($commandLine -notmatch '(?i)-m\s+uvicorn\s+acis\.api\.app:app' -or
            $commandLine -notmatch '(?i)--host\s+127\.0\.0\.1' -or
            $commandLine -notmatch $portPattern -or
            $commandLine -notmatch $appDirectoryPattern) {
            return $null
        }
        return $process
    } catch {
        return $null
    }
}

function Read-LaunchRecord {
    if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) {
        return $null
    }
    try {
        $record = Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not [string]$record.root -or
            -not ([string]$record.root).Equals($Root, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $null
        }
        return $record
    } catch {
        return $null
    }
}

function Remove-LaunchRecord {
    if (Test-Path -LiteralPath $StatePath -PathType Leaf) {
        Remove-Item -LiteralPath $StatePath -Force
    }
}

function Stop-OwnedProcess($Record) {
    $process = Get-ProcessIdentity $Record
    if (-not $process) {
        return $false
    }
    $processHandle = $null
    try {
        $processHandle = [System.Diagnostics.Process]::GetProcessById([int]$Record.pid)
        $expectedStart = [DateTimeOffset]::Parse([string]$Record.started_utc).UtcDateTime
        $actualStart = $processHandle.StartTime.ToUniversalTime()
        if ([Math]::Abs(($actualStart - $expectedStart).TotalSeconds) -gt 2) {
            return $false
        }
        $processHandle.Kill()
        return $processHandle.WaitForExit(10000)
    } catch {
        return $false
    } finally {
        if ($processHandle) {
            $processHandle.Dispose()
        }
    }
}

function Test-PortAvailable([int]$Value) {
    $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Value)
    try {
        $listener.Start()
        return $true
    } catch [System.Net.Sockets.SocketException] {
        return $false
    } finally {
        if ($listener.Server.IsBound) {
            $listener.Stop()
        }
    }
}

function Get-HealthResponse([System.Net.Http.HttpClient]$Client, [string]$Url) {
    try {
        $response = $Client.GetAsync($Url).GetAwaiter().GetResult()
        $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        return @{ status = [int]$response.StatusCode; body = $body }
    } catch {
        return @{ status = 0; body = "" }
    }
}

function Open-Workbench([string]$Url) {
    try {
        Start-Process -FilePath $Url | Out-Null
        Write-Info "已请求打开默认浏览器：$Url"
    } catch {
        Write-WarningMessage "浏览器无法自动打开，请手动访问：$Url"
    }
}

function Start-ACIS {
    $selectedPort = Get-PortValue
    $script:BaseUrl = "http://127.0.0.1:$selectedPort"
    $envPath = Join-Path $Root ".env"
    if (-not $env:ACIS_API_KEY -and -not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
        throw "没有发现 .env 或进程环境变量 ACIS_API_KEY。请复制 .env.example 为 .env 并设置至少 32 个 ASCII 字符的本地密钥；启动器不会读取或覆盖密钥文件。"
    }
    if ($env:ACIS_API_KEY) {
        if ($env:ACIS_API_KEY.Length -lt 32 -or $env:ACIS_API_KEY -match '[^\x00-\x7F]') {
            throw "进程环境变量 ACIS_API_KEY 不符合要求（至少 32 个 ASCII 字符）。密钥值不会输出。"
        }
    }

    $python = Get-PythonPath
    $versionText = & $python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
    if ($LASTEXITCODE -ne 0) {
        throw "无法运行 Python：$python"
    }
    $version = [Version]$versionText.Trim()
    if ($version.Major -lt 3 -or ($version.Major -eq 3 -and $version.Minor -lt 11)) {
        throw "需要 Python 3.11 或更高版本，当前检测到 $version。"
    }
    Write-Info "Python $version：$python"

    if (-not (Test-Path -LiteralPath (Join-Path $Root "web\dist\index.html") -PathType Leaf)) {
        throw "未找到 Vue 生产构建 web\dist\index.html。请在 web 目录执行 npm ci 后 npm run build。"
    }
    $assetFiles = Get-ChildItem -LiteralPath (Join-Path $Root "web\dist\assets") -File -ErrorAction SilentlyContinue
    if (-not $assetFiles) {
        throw "web\dist\assets 中没有前端资源。请在 web 目录执行 npm ci 后 npm run build。"
    }

    Push-Location $Root
    try {
        & $python -c "import acis.api.app; print('ACIS backend imports: OK')"
        if ($LASTEXITCODE -ne 0) {
            throw "后端依赖导入失败。请在当前 Python 环境安装 requirements.txt，并检查启动日志。"
        }
    } finally {
        Pop-Location
    }

    $record = Read-LaunchRecord
    $recordProcess = if ($record) { Get-ProcessIdentity $record } else { $null }
    if ($recordProcess -and [int]$record.port -ne $selectedPort) {
        throw "本启动器已在端口 $($record.port) 管理 ACIS（PID $($record.pid)）。请先运行 stop_acis.bat，再更改端口。"
    }
    if ($recordProcess -and [int]$record.port -eq $selectedPort) {
        $handler = New-Object System.Net.Http.HttpClientHandler
        $handler.UseProxy = $false
        $client = New-Object System.Net.Http.HttpClient($handler)
        try {
            $health = Get-HealthResponse $client "$BaseUrl/health"
        } finally {
            $client.Dispose()
            $handler.Dispose()
        }
        if ($health.status -eq 200) {
            Write-Info "本次启动的 ACIS 已运行。"
            Open-Workbench $BaseUrl
            return
        }
        throw "已记录的 ACIS 进程仍存在，但健康检查未通过（HTTP $($health.status)）。日志：$($record.stderr_log)"
    }

    if (-not (Test-PortAvailable $selectedPort)) {
        throw "端口 $selectedPort 已被占用。未终止占用进程；请检查端口或用 -Port / ACIS_LOCAL_PORT 选择其他端口。"
    }

    $logId = "$(Get-Date -Format 'yyyyMMdd-HHmmss')-$([Guid]::NewGuid().ToString('N').Substring(0, 8))"
    $logsDirectory = Join-Path $Root "logs"
    New-Item -ItemType Directory -Path $logsDirectory -Force | Out-Null
    $script:StdoutLog = Join-Path $logsDirectory "acis-local-$logId.out.log"
    $script:StderrLog = Join-Path $logsDirectory "acis-local-$logId.err.log"
    $argumentLine = "-m uvicorn acis.api.app:app --host 127.0.0.1 --port $selectedPort --app-dir `"$Root`""
    $script:ServerProcess = Start-Process -FilePath $python -ArgumentList $argumentLine -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog
    $processDetails = Get-Process -Id $ServerProcess.Id -ErrorAction Stop
    $record = [ordered]@{
        root = $Root
        pid = $ServerProcess.Id
        python = [System.IO.Path]::GetFullPath($python)
        started_utc = $processDetails.StartTime.ToUniversalTime().ToString("o")
        port = $selectedPort
        stdout_log = $StdoutLog
        stderr_log = $StderrLog
    }
    $script:LaunchRecord = $record
    $temporaryStatePath = "$StatePath.$([Guid]::NewGuid().ToString('N')).tmp"
    $record | ConvertTo-Json | Set-Content -LiteralPath $temporaryStatePath -Encoding UTF8
    Move-Item -LiteralPath $temporaryStatePath -Destination $StatePath -Force

    $handler = New-Object System.Net.Http.HttpClientHandler
    $handler.UseProxy = $false
    $client = New-Object System.Net.Http.HttpClient($handler)
    $healthy = $false
    $healthDetail = "健康检查超时"
    try {
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            if (-not (Get-ProcessIdentity $record)) {
                $healthDetail = "API 进程已退出"
                break
            }
            $health = Get-HealthResponse $client "$BaseUrl/health"
            if ($health.status -eq 200) {
                $healthy = $true
                break
            }
            if ($health.status -eq 503) {
                $healthDetail = "API 健康检查返回 HTTP 503；请确认 .env 或进程环境变量中的 ACIS_API_KEY 至少 32 个 ASCII 字符。密钥值不会输出。"
                break
            }
            Start-Sleep -Seconds 1
        }
    } finally {
        $client.Dispose()
        $handler.Dispose()
    }

    if (-not $healthy) {
        if (Stop-OwnedProcess $record) {
            Remove-LaunchRecord
        }
        Write-Failure "$healthDetail。日志：$StderrLog"
        exit 1
    }

    Write-Info "ACIS API 健康检查通过。"
    Write-Info "Web 工作台：$BaseUrl"
    Write-Info "运行日志：$StdoutLog"
    Write-Info "错误日志：$StderrLog"
    Open-Workbench $BaseUrl
}

function Stop-ACIS {
    $record = Read-LaunchRecord
    if (-not $record) {
        Write-WarningMessage "没有本启动器的进程记录；未终止任何进程。"
        return
    }
    $process = Get-ProcessIdentity $record
    if (-not $process) {
        Remove-LaunchRecord
        Write-WarningMessage "本启动器记录的进程已退出或 PID 已复用；仅清除本启动器记录。"
        return
    }
    if (Stop-OwnedProcess $record) {
        Remove-LaunchRecord
        Write-Info "已安全停止本启动器的 ACIS 进程 PID $($record.pid)。"
        Write-Info "日志已保留：$($record.stdout_log)"
    } else {
        Write-WarningMessage "进程身份校验或停止未完成；未强制终止进程，也保留了启动记录。"
    }
}

$StatePath = Get-StatePath
$stateId = [System.IO.Path]::GetFileNameWithoutExtension($StatePath)
$launcherMutex = New-Object System.Threading.Mutex($false, "Local\ACIS_LocalLauncher_$stateId")
$hasMutex = $false
try {
    try {
        $hasMutex = $launcherMutex.WaitOne([TimeSpan]::FromSeconds(120))
    } catch [System.Threading.AbandonedMutexException] {
        $hasMutex = $true
        Write-WarningMessage "检测到上次启动器异常退出，正在安全检查状态记录。"
    }
    if (-not $hasMutex) {
        throw "另一个 ACIS 启停操作仍在进行。请稍后重试。"
    }
    if ($Action -eq "start") {
        Start-ACIS
    } else {
        Stop-ACIS
    }
} catch {
    Write-Failure $_.Exception.Message
    if ($Action -eq "start" -and $ServerProcess -and $StatePath) {
        $record = $LaunchRecord
        if (-not $record) {
            $record = Read-LaunchRecord
        }
        if ($record -and (Stop-OwnedProcess $record)) {
            $currentRecord = Read-LaunchRecord
            if ($currentRecord -and [int]$currentRecord.pid -eq [int]$record.pid) {
                Remove-LaunchRecord
            }
        }
    }
    if ($Action -eq "start") {
        if ($StderrLog) {
            Write-Host "[ACIS] 错误日志：$StderrLog" -ForegroundColor Yellow
        } else {
            $logDirectory = Join-Path $Root "logs"
            New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
            Write-Host "[ACIS] 服务日志目录：$logDirectory（本次失败发生在服务启动前，尚无服务日志）" -ForegroundColor Yellow
        }
    }
    exit 1
} finally {
    if ($hasMutex) {
        $launcherMutex.ReleaseMutex()
    }
    $launcherMutex.Dispose()
}
