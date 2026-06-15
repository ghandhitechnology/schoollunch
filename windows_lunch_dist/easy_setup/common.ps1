# ============================================================================
#  common.ps1 — 하태욱 프로그램 Windows 설치 공용 라이브러리
# ----------------------------------------------------------------------------
#  이 파일은 dot-source 로 불러 쓴다.  예)  . "$PSScriptRoot\common.ps1"
#  setup_master.ps1 과 methods\method_*.ps1 가 모두 이 한 파일을 공유한다.
#
#  주의: 이 파일은 모듈(.psm1)이 아니라 스크립트(.ps1)이므로
#        Export-ModuleMember 를 쓰지 않는다. dot-source 하면 함수가
#        호출자 스코프로 그대로 들어온다.
# ============================================================================

$OutputEncoding = [System.Text.Encoding]::UTF8
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

# ── 경로 계산 ────────────────────────────────────────────────────────────────
# 이 파일은 windows_lunch_dist\easy_setup\common.ps1 위치에 있다.
# 따라서 프로젝트 루트는 easy_setup 의 상위 폴더다.
$script:EasySetupDir = $PSScriptRoot
$script:ProjectRoot  = Split-Path -Parent $PSScriptRoot

function Get-SetupContext {
    <#
        설치에 필요한 모든 경로/이름을 한 객체로 돌려준다.
        모든 method 스크립트가 이걸 받아서 동작한다.
    #>
    $appName    = "하태욱 프로그램"
    $appDirName = "하태욱프로그램"
    $exeName    = "하태욱 프로그램.exe"
    $installDir = Join-Path $env:LOCALAPPDATA $appDirName
    $startMenu  = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"

    return [PSCustomObject]@{
        AppName          = $appName
        AppDirName       = $appDirName
        ExeName          = $exeName
        ProjectRoot      = $script:ProjectRoot
        EasySetupDir     = $script:EasySetupDir
        MethodsDir       = Join-Path $script:EasySetupDir "methods"
        InstallDir       = $installDir
        DataDir          = Join-Path $env:APPDATA $appDirName
        VenvDir          = Join-Path $script:ProjectRoot ".venv"
        RequirementsFile = Join-Path $script:ProjectRoot "requirements.txt"
        SpecFile         = Join-Path $script:ProjectRoot "windows_build.spec"
        MainPy           = Join-Path $script:ProjectRoot "main.py"
        AssetsDir        = Join-Path $script:ProjectRoot "assets"
        WheelsDir        = Join-Path $script:ProjectRoot "wheels"
        PrebuiltExe      = Join-Path (Join-Path $script:ProjectRoot "prebuilt") $exeName
        DistExe          = Join-Path (Join-Path $script:ProjectRoot "dist") $exeName
        StartMenuLnk     = Join-Path $startMenu "$appName.lnk"
        DesktopLnk       = Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk"
        InstalledExe     = Join-Path $installDir $exeName
        InstalledRunBat  = Join-Path $installDir "run.bat"
        LogFile          = Join-Path (Join-Path $env:APPDATA $appDirName) "setup.log"
        PythonVersion    = "3.12.4"
    }
}

# ── 로깅 / 화면 출력 ─────────────────────────────────────────────────────────
$script:LogFilePath = $null

function Initialize-Logging {
    param([string]$LogFile)
    $script:LogFilePath = $LogFile
    $dir = Split-Path -Parent $LogFile
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

function Write-SetupLog {
    param(
        [string]$Message,
        [ValidateSet("INFO", "STEP", "OK", "WARN", "ERROR")]
        [string]$Level = "INFO"
    )
    $colors = @{ INFO = "Gray"; STEP = "Cyan"; OK = "Green"; WARN = "Yellow"; ERROR = "Red" }
    $prefix = @{ INFO = "    "; STEP = "==> "; OK = "[OK] "; WARN = "[!] "; ERROR = "[X] " }
    Write-Host ("{0}{1}" -f $prefix[$Level], $Message) -ForegroundColor $colors[$Level]

    if ($script:LogFilePath) {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        try { "$stamp [$Level] $Message" | Out-File -FilePath $script:LogFilePath -Append -Encoding UTF8 } catch { }
    }
}

function Write-Step { param([string]$m) Write-SetupLog $m "STEP" }
function Write-Ok   { param([string]$m) Write-SetupLog $m "OK" }
function Write-Warn { param([string]$m) Write-SetupLog $m "WARN" }
function Write-Fail { param([string]$m) Write-SetupLog $m "ERROR" }
function Write-Info { param([string]$m) Write-SetupLog $m "INFO" }

function Show-Banner {
    param([string]$Title)
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor DarkCyan
    Write-Host "   $Title" -ForegroundColor White
    Write-Host "================================================================" -ForegroundColor DarkCyan
    Write-Host ""
}

function Pause-ForUser {
    param([string]$Message = "Enter 키를 누르면 창이 닫힙니다")
    try { Read-Host $Message | Out-Null } catch { }
}

function Write-PlainText {
    <#
        BOM 없는 UTF-8 로 텍스트 파일을 쓴다.
        Windows PowerShell 5.1 의 Set-Content -Encoding UTF8 은 BOM 을 붙이는데,
        .bat/.cmd 의 맨 앞 BOM 은 첫 줄(@echo off)을 깨뜨리므로 반드시 BOM 없이 써야 한다.
    #>
    param([string]$Path, [string]$Content)
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

function Read-YesNo {
    param([string]$Prompt, [bool]$DefaultYes = $true)
    $suffix = if ($DefaultYes) { "(Y/n)" } else { "(y/N)" }
    $answer = Read-Host "$Prompt $suffix"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
    return $answer -match "^(y|yes|예|ㅛ)$"
}

# ── 권한 / 환경 ──────────────────────────────────────────────────────────────
function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($id)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ── 안전한 작업 경로 ─────────────────────────────────────────────────────────
function Test-SafePath {
    param([string]$Path)
    # 공백/한글이 섞인 경로는 PyInstaller·pip 에서 가끔 문제를 일으킨다.
    if ($Path -match '\s') { return $false }
    if ($Path -match '[^\x00-\x7F]') { return $false }
    return $true
}

# ── Python 탐색 ──────────────────────────────────────────────────────────────
function Find-Python {
    <#
        쓸 만한 Python(3.10+)을 찾아 실행 경로를 돌려준다. 없으면 $null.
        Windows Store 의 가짜(python.exe stub) 는 건너뛴다.
    #>
    $candidates = @()
    foreach ($cmd in @("python", "python3", "py")) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) { $candidates += $found.Source }
    }
    # 자주 쓰이는 설치 경로도 직접 확인한다.
    $candidates += @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe"
    )

    foreach ($path in $candidates) {
        if (-not $path -or -not (Test-Path $path)) { continue }
        if ((Split-Path -Parent $path) -like "*WindowsApps*") { continue }  # Store stub
        try {
            $verStr = & $path --version 2>&1
            if ($verStr -match "Python (\d+)\.(\d+)") {
                $major = [int]$matches[1]; $minor = [int]$matches[2]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
                    return $path
                }
            }
        } catch { }
    }
    return $null
}

function Install-PythonSilently {
    <#
        python.org 에서 Python 설치 파일을 받아 사용자 계정용으로 조용히 설치한다.
        성공 시 설치된 python.exe 경로, 실패 시 $null.
    #>
    param([string]$Version = "3.12.4")
    $url = "https://www.python.org/ftp/python/$Version/python-$Version-amd64.exe"
    $installer = Join-Path $env:TEMP "python-$Version-amd64.exe"
    if (-not (Get-DownloadedFile -Url $url -OutPath $installer)) {
        Write-Warn "Python 설치 파일을 내려받지 못했습니다."
        return $null
    }
    Write-Info "Python 설치 중... (1~3분 걸릴 수 있습니다)"
    try {
        Start-Process -FilePath $installer `
            -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0" `
            -Wait
    } catch {
        Write-Warn "Python 자동 설치 실패: $_"
        return $null
    }
    # PATH 갱신을 즉시 반영하기 위해 직접 경로를 다시 찾는다.
    return Find-Python
}

# ── 네트워크 ─────────────────────────────────────────────────────────────────
function Test-Internet {
    foreach ($url in @("https://pypi.org", "https://www.python.org")) {
        try {
            $resp = Invoke-WebRequest -Uri $url -TimeoutSec 6 -UseBasicParsing
            if ($resp.StatusCode -eq 200) { return $true }
        } catch { }
    }
    return $false
}

function Get-SystemProxy {
    $proxy = (Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" `
                -Name ProxyServer -ErrorAction SilentlyContinue).ProxyServer
    if ($proxy) { return "http://$proxy" }
    return $null
}

function Get-DownloadedFile {
    param([string]$Url, [string]$OutPath, [int]$MaxRetries = 3)
    $proxy = Get-SystemProxy
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            if ($proxy) {
                Invoke-WebRequest -Uri $Url -OutFile $OutPath -UseBasicParsing -TimeoutSec 180 -Proxy $proxy
            } else {
                Invoke-WebRequest -Uri $Url -OutFile $OutPath -UseBasicParsing -TimeoutSec 180
            }
            if (Test-Path $OutPath) { return $true }
        } catch {
            Write-Info "다운로드 재시도 $i/$MaxRetries ..."
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

# ── 가상 환경 ────────────────────────────────────────────────────────────────
function New-Venv {
    <# 가상 환경을 새로 만들고 venv 안의 python.exe 경로를 돌려준다. 실패 시 $null #>
    param([string]$PythonExe, [string]$VenvDir)
    if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue }
    try {
        & $PythonExe -m venv "$VenvDir"
        $venvPython = Join-Path $VenvDir "Scripts\python.exe"
        if (Test-Path $venvPython) { return $venvPython }
    } catch {
        Write-Warn "가상 환경 생성 실패: $_"
    }
    return $null
}

# ── pip 패키지 설치 ──────────────────────────────────────────────────────────
function Install-Packages {
    <#
        requirements.txt 를 설치한다.
        -User      : 가상 환경 없이 사용자 영역(--user)에 설치
        -IndexUrl  : 대체 미러(예: 사내/국내 미러) 사용
        -NoIndex/-FindLinks : 오프라인(번들 wheel) 설치
        성공 시 $true.
    #>
    param(
        [string]$PythonExe,
        [string]$RequirementsFile,
        [switch]$User,
        [string]$IndexUrl,
        [switch]$Offline,
        [string]$FindLinks,
        [int]$MaxRetries = 3
    )
    $common = @("install", "-r", $RequirementsFile, "--disable-pip-version-check")
    if ($User)    { $common += "--user" }
    if ($IndexUrl){ $common += @("--index-url", $IndexUrl) }
    if ($Offline) { $common += @("--no-index", "--find-links", $FindLinks) }
    $proxy = Get-SystemProxy
    if ($proxy -and -not $Offline) { $common += @("--proxy", $proxy) }

    # pip 자체 업그레이드 (오프라인이 아니면)
    if (-not $Offline) {
        try { & $PythonExe -m pip install --upgrade pip --disable-pip-version-check 2>&1 | Out-Null } catch { }
    }

    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            & $PythonExe -m pip @common
            if ($LASTEXITCODE -eq 0) { return $true }
        } catch { }
        Write-Info "패키지 설치 재시도 $i/$MaxRetries ..."
        Start-Sleep -Seconds 2
    }
    return $false
}

# ── 빌드 ─────────────────────────────────────────────────────────────────────
function Build-Exe {
    <# PyInstaller 로 exe 를 만든다. 성공 시 dist 의 exe 경로, 실패 시 $null #>
    param([string]$PythonExe, [object]$Ctx)
    try {
        & $PythonExe -m pip install pyinstaller --disable-pip-version-check 2>&1 | Out-Null
        & $PythonExe -m PyInstaller --noconfirm --clean "$($Ctx.SpecFile)"
        if ($LASTEXITCODE -eq 0 -and (Test-Path $Ctx.DistExe)) { return $Ctx.DistExe }
    } catch {
        Write-Warn "빌드 실패: $_"
    }
    return $null
}

# ── 바로가기 ─────────────────────────────────────────────────────────────────
function New-Shortcut {
    <#
        .lnk 바로가기를 만든다. COM(WScript.Shell)이 막히면 .cmd 런처로 대체한다.
    #>
    param(
        [string]$TargetPath,
        [string]$ShortcutPath,
        [string]$WorkingDirectory,
        [string]$Arguments = "",
        [string]$IconLocation = ""
    )
    $dir = Split-Path -Parent $ShortcutPath
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    try {
        $wsh = New-Object -ComObject WScript.Shell
        $sc = $wsh.CreateShortcut($ShortcutPath)
        $sc.TargetPath = $TargetPath
        $sc.WorkingDirectory = $WorkingDirectory
        if ($Arguments)    { $sc.Arguments = $Arguments }
        if ($IconLocation) { $sc.IconLocation = $IconLocation }
        $sc.Save()
        return $true
    } catch {
        # COM 실패 → 동일 위치에 .cmd 런처 생성 (바로가기 대체)
        $cmd = [System.IO.Path]::ChangeExtension($ShortcutPath, ".cmd")
        $body = "@echo off`r`nchcp 65001 >nul`r`ncd /d `"$WorkingDirectory`"`r`nstart `"`" `"$TargetPath`" $Arguments`r`n"
        Write-PlainText -Path $cmd -Content $body
        Write-Warn "바로가기 COM 생성 실패 — 대신 런처를 만들었습니다: $cmd"
        return (Test-Path $cmd)
    }
}

function New-AppShortcuts {
    <# 시작 메뉴 바로가기(필수) + 선택적으로 바탕화면 바로가기를 만든다. #>
    param([object]$Ctx, [string]$TargetPath, [string]$Arguments = "", [bool]$Desktop = $true)
    $icon = if (Test-Path $Ctx.InstalledExe) { "$($Ctx.InstalledExe),0" } else { "" }
    New-Shortcut -TargetPath $TargetPath -ShortcutPath $Ctx.StartMenuLnk `
        -WorkingDirectory $Ctx.InstallDir -Arguments $Arguments -IconLocation $icon | Out-Null
    if ($Desktop) {
        New-Shortcut -TargetPath $TargetPath -ShortcutPath $Ctx.DesktopLnk `
            -WorkingDirectory $Ctx.InstallDir -Arguments $Arguments -IconLocation $icon | Out-Null
    }
}

# ── 설치 (exe 방식) ──────────────────────────────────────────────────────────
function Install-ExeProgram {
    <# 빌드/번들된 exe 를 설치 폴더로 복사하고 바로가기를 만든다. #>
    param([object]$Ctx, [string]$ExePath, [bool]$Desktop = $true)
    if (-not (Test-Path $ExePath)) { return $false }
    if (-not (Test-Path $Ctx.InstallDir)) { New-Item -ItemType Directory -Path $Ctx.InstallDir -Force | Out-Null }
    Get-ChildItem -Path $Ctx.InstallDir -Filter "*.exe" -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
    Copy-Item -Path $ExePath -Destination $Ctx.InstalledExe -Force
    New-AppShortcuts -Ctx $Ctx -TargetPath $Ctx.InstalledExe -Desktop $Desktop
    return $true
}

# ── 설치 (소스 실행 방식) ────────────────────────────────────────────────────
function Install-SourceProgram {
    <#
        exe 빌드 없이 소스(*.py)와 Python 런타임을 설치 폴더로 복사하고
        더블클릭으로 실행할 run.bat 런처와 바로가기를 만든다.
        $PythonExe 는 venv 또는 임베디드 python.exe 경로.
    #>
    param([object]$Ctx, [string]$PythonExe, [bool]$Desktop = $true)
    if (-not (Test-Path $Ctx.InstallDir)) { New-Item -ItemType Directory -Path $Ctx.InstallDir -Force | Out-Null }

    Copy-Item -Path (Join-Path $Ctx.ProjectRoot "*.py") -Destination $Ctx.InstallDir -Force
    if (Test-Path $Ctx.AssetsDir) {
        Copy-Item -Path $Ctx.AssetsDir -Destination $Ctx.InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    # Python 런타임을 설치 폴더 안으로 함께 복사해 이식성을 확보한다.
    $runtimeDir = Join-Path $Ctx.InstallDir "runtime"
    $pythonSource = Split-Path -Parent $PythonExe   # ...\Scripts 또는 임베디드 폴더
    if ($pythonSource -like "*\Scripts") { $pythonSource = Split-Path -Parent $pythonSource }  # venv 루트
    if (Test-Path $runtimeDir) { Remove-Item -Recurse -Force $runtimeDir -ErrorAction SilentlyContinue }
    Copy-Item -Path $pythonSource -Destination $runtimeDir -Recurse -Force -ErrorAction SilentlyContinue

    # 복사된 런타임 안에서 pythonw.exe(콘솔 없는 실행기)를 찾는다.
    $pyw = @(
        (Join-Path $runtimeDir "Scripts\pythonw.exe"),
        (Join-Path $runtimeDir "pythonw.exe"),
        (Join-Path $runtimeDir "Scripts\python.exe"),
        (Join-Path $runtimeDir "python.exe")
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $pyw) { $pyw = $PythonExe }   # 복사 실패 시 원본 사용 (이식성은 떨어짐)

    $relPyw = $pyw.Replace($Ctx.InstallDir, "%~dp0").Replace("%~dp0\", "%~dp0")
    $runBat = @"
@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "$relPyw" "%~dp0main.py" %*
"@
    Write-PlainText -Path $Ctx.InstalledRunBat -Content $runBat

    New-AppShortcuts -Ctx $Ctx -TargetPath $Ctx.InstalledRunBat -Desktop $Desktop
    return $true
}

# ── Windows Defender 예외 ────────────────────────────────────────────────────
function Add-DefenderExclusion {
    param([string]$Path)
    try {
        Add-MpPreference -ExclusionPath $Path -ErrorAction Stop
        Write-Ok "Windows Defender 예외 추가: $Path"
        return $true
    } catch {
        Write-Warn "Defender 예외 추가 실패(권한 또는 다른 백신 사용 중일 수 있음): $Path"
        return $false
    }
}

# ── 검증 ─────────────────────────────────────────────────────────────────────
function Test-Installation {
    <# 설치가 실제로 됐는지 확인: 실행 대상(exe 또는 run.bat) + 시작 메뉴 바로가기 #>
    param([object]$Ctx)
    $hasTarget = (Test-Path $Ctx.InstalledExe) -or (Test-Path $Ctx.InstalledRunBat)
    $hasShortcut = (Test-Path $Ctx.StartMenuLnk) -or
                   (Test-Path ([System.IO.Path]::ChangeExtension($Ctx.StartMenuLnk, ".cmd")))
    return ($hasTarget -and $hasShortcut)
}

function Start-InstalledApp {
    param([object]$Ctx)
    try {
        if (Test-Path $Ctx.InstalledExe) {
            Start-Process -FilePath $Ctx.InstalledExe
        } elseif (Test-Path $Ctx.InstalledRunBat) {
            Start-Process -FilePath $Ctx.InstalledRunBat
        }
    } catch {
        Write-Warn "프로그램 실행 실패: $_"
    }
}
