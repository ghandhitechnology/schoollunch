param(
    [switch]$BuildOnly,
    [switch]$InstallOnly,
    [switch]$NoAutoStart,
    [switch]$NoDesktopShortcut,
    [switch]$NoSafeCopy,
    [switch]$PreferExistingExe,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$script:Root = $PSScriptRoot
Set-Location -Path $script:Root

function New-Context {
    $appName = "하태욱 프로그램"
    $appDirName = "하태욱프로그램"
    $exeName = "하태욱 프로그램.exe"
    $installDir = Join-Path $env:LOCALAPPDATA $appDirName
    $dataDir = Join-Path $env:APPDATA $appDirName
    $startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"

    [PSCustomObject]@{
        AppName = $appName
        AppDirName = $appDirName
        ExeName = $exeName
        Root = $script:Root
        InstallDir = $installDir
        DataDir = $dataDir
        LogFile = Join-Path $dataDir "setup.log"
        VenvDir = Join-Path $script:Root ".venv"
        Requirements = Join-Path $script:Root "requirements.txt"
        SpecFile = Join-Path $script:Root "windows_build.spec"
        MainPy = Join-Path $script:Root "main.py"
        AssetsDir = Join-Path $script:Root "assets"
        IconFile = Join-Path $script:Root "assets\icons\app_icon.ico"
        DistExe = Join-Path (Join-Path $script:Root "dist") $exeName
        PrebuiltExe = Join-Path (Join-Path $script:Root "prebuilt") $exeName
        InstalledExe = Join-Path $installDir $exeName
        InstalledRunBat = Join-Path $installDir "run_source.bat"
        StartMenuLink = Join-Path $startMenu "$appName.lnk"
        DesktopLink = Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk"
        PythonVersion = "3.12.4"
        TaskName = $appDirName
    }
}

$Ctx = New-Context

function Initialize-Log {
    if (-not (Test-Path $Ctx.DataDir)) {
        New-Item -ItemType Directory -Path $Ctx.DataDir -Force | Out-Null
    }
}

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("INFO", "STEP", "OK", "WARN", "ERROR")]
        [string]$Level = "INFO"
    )
    $colors = @{ INFO = "Gray"; STEP = "Cyan"; OK = "Green"; WARN = "Yellow"; ERROR = "Red" }
    $prefix = @{ INFO = "    "; STEP = "==> "; OK = "[OK] "; WARN = "[!] "; ERROR = "[X] " }
    Write-Host ("{0}{1}" -f $prefix[$Level], $Message) -ForegroundColor $colors[$Level]
    try {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "$stamp [$Level] $Message" | Out-File -FilePath $Ctx.LogFile -Append -Encoding UTF8
    } catch { }
}

function Write-Step { param([string]$Message) Write-Log $Message "STEP" }
function Write-Ok { param([string]$Message) Write-Log $Message "OK" }
function Write-Warn { param([string]$Message) Write-Log $Message "WARN" }
function Write-Fail { param([string]$Message) Write-Log $Message "ERROR" }
function Write-Info { param([string]$Message) Write-Log $Message "INFO" }

function Pause-End {
    param([int]$Code)
    if (-not $env:CI) {
        try { Read-Host "Enter 키를 누르면 창이 닫힙니다" | Out-Null } catch { }
    }
    exit $Code
}

function Show-Banner {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor DarkCyan
    Write-Host "   하태욱 프로그램 - 최종 Windows 빌드/설치" -ForegroundColor White
    Write-Host "================================================================" -ForegroundColor DarkCyan
    Write-Host ""
}

function Write-PlainText {
    param([string]$Path, [string]$Content)
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

function Test-Windows {
    return [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
}

function Test-SafeBuildPath {
    param([string]$Path)
    if ($Path -match '\s') { return $false }
    if ($Path -match '[^\x00-\x7F]') { return $false }
    return $true
}

function Copy-PackageToSafePath {
    param([string]$Target)
    try {
        if (Test-Path $Target) {
            Remove-Item -Recurse -Force $Target -ErrorAction Stop
        }
        New-Item -ItemType Directory -Path $Target -Force -ErrorAction Stop | Out-Null
        $robocopy = Get-Command robocopy -ErrorAction SilentlyContinue
        if ($robocopy) {
            & robocopy "$script:Root" "$Target" /MIR /XD ".venv" "build" "dist" "__pycache__" /XF "*.pyc" "*.pyo" "*.zip" /NFL /NDL /NJH /NJS /NP | Out-Null
            if ($LASTEXITCODE -le 7) { return $true }
            return $false
        }
        Get-ChildItem -Path $script:Root -Force |
            Where-Object { $_.Name -notin @(".venv", "build", "dist", "__pycache__") -and $_.Extension -ne ".zip" } |
            Copy-Item -Destination $Target -Recurse -Force -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Invoke-SafePathRerun {
    if ($NoSafeCopy -or (Test-SafeBuildPath $script:Root)) { return }

    Write-Warn "현재 경로에 공백/한글이 있어 Windows 빌드 도구가 실패할 수 있습니다."
    Write-Info "안전한 ASCII 경로로 복사한 뒤 그 위치에서 다시 실행합니다."

    $targets = @("C:\schoollunch_final_build")
    if ($env:PUBLIC) { $targets += (Join-Path $env:PUBLIC "schoollunch_final_build") }
    if ($env:LOCALAPPDATA) { $targets += (Join-Path $env:LOCALAPPDATA "schoollunch_final_build") }

    foreach ($target in $targets) {
        Write-Info "복사 시도: $target"
        if (Copy-PackageToSafePath -Target $target) {
            $safeScript = Join-Path $target "setup_windows_final.ps1"
            $psArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $safeScript, "-NoSafeCopy")
            if ($BuildOnly) { $psArgs += "-BuildOnly" }
            if ($InstallOnly) { $psArgs += "-InstallOnly" }
            if ($NoAutoStart) { $psArgs += "-NoAutoStart" }
            if ($NoDesktopShortcut) { $psArgs += "-NoDesktopShortcut" }
            if ($PreferExistingExe) { $psArgs += "-PreferExistingExe" }
            if ($SkipTests) { $psArgs += "-SkipTests" }
            $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $psArgs -Wait -PassThru
            exit $proc.ExitCode
        }
    }

    Write-Warn "안전 경로 복사에 실패했습니다. 현재 위치에서 계속 진행합니다."
}

function Test-RequiredFiles {
    $required = @(
        $Ctx.MainPy,
        $Ctx.Requirements,
        $Ctx.SpecFile,
        (Join-Path $Ctx.Root "windows_manifest.xml"),
        (Join-Path $Ctx.Root "windows_version_info.txt"),
        $Ctx.IconFile,
        (Join-Path $Ctx.AssetsDir "fonts\neodgm.ttf"),
        (Join-Path $Ctx.Root "app_ui.py"),
        (Join-Path $Ctx.Root "fetch_meal.py"),
        (Join-Path $Ctx.Root "fetch_timetable.py"),
        (Join-Path $Ctx.Root "render.py"),
        (Join-Path $Ctx.Root "wallpaper.py")
    )
    $missing = @($required | Where-Object { -not (Test-Path $_) })
    if ($missing.Count -gt 0) {
        foreach ($file in $missing) { Write-Fail "필수 파일 없음: $file" }
        return $false
    }
    return $true
}

function Test-PythonExecutable {
    param([string]$PythonExe)
    if (-not $PythonExe -or -not (Test-Path $PythonExe)) { return $false }
    if ((Split-Path -Parent $PythonExe) -like "*WindowsApps*") { return $false }
    try {
        $version = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $version) { return $false }
        if ($version -match '^(\d+)\.(\d+)') {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            return ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10))
        }
    } catch { }
    return $false
}

function Find-Python {
    $candidates = New-Object System.Collections.Generic.List[string]

    foreach ($cmdName in @("python", "python3")) {
        $cmd = Get-Command $cmdName -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source) { [void]$candidates.Add($cmd.Source) }
    }

    foreach ($path in @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe"
    )) {
        [void]$candidates.Add($path)
    }

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher -and $pyLauncher.Source) {
        try {
            $launcherPython = & $pyLauncher.Source -3 -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1
            if ($launcherPython) { [void]$candidates.Add($launcherPython.Trim()) }
        } catch { }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-PythonExecutable $candidate) { return $candidate }
    }
    return $null
}

function Refresh-Path {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $env:Path = "$userPath;$machinePath"
}

function Get-DownloadedFile {
    param([string]$Url, [string]$OutPath)
    for ($i = 1; $i -le 3; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -OutFile $OutPath -UseBasicParsing -TimeoutSec 180
            if (Test-Path $OutPath) { return $true }
        } catch {
            Write-Warn "다운로드 재시도 $i/3: $Url"
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

function Install-PythonForUser {
    $version = $Ctx.PythonVersion
    $installer = Join-Path $env:TEMP "python-$version-amd64.exe"
    $url = "https://www.python.org/ftp/python/$version/python-$version-amd64.exe"

    Write-Step "Python $version 사용자 설치"
    Write-Info "다운로드: $url"
    if (-not (Get-DownloadedFile -Url $url -OutPath $installer)) {
        Write-Fail "Python 설치 파일을 다운로드하지 못했습니다."
        return $null
    }

    Write-Info "Python 설치 중입니다. 1~3분 걸릴 수 있습니다."
    Start-Process -FilePath $installer `
        -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0 Include_launcher=1" `
        -Wait
    Refresh-Path
    return Find-Python
}

function New-BuildVenv {
    param([string]$PythonExe)
    if (Test-Path $Ctx.VenvDir) {
        Remove-Item -Recurse -Force $Ctx.VenvDir -ErrorAction SilentlyContinue
    }
    Write-Step "빌드 가상환경 생성"
    & $PythonExe -m venv $Ctx.VenvDir
    $venvPython = Join-Path $Ctx.VenvDir "Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        throw "가상환경 python.exe 생성 실패: $venvPython"
    }
    return $venvPython
}

function Install-Packages {
    param([string]$PythonExe)
    Write-Step "Python 패키지 설치"
    & $PythonExe -m pip install --upgrade pip setuptools wheel --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { return $false }
    & $PythonExe -m pip install -r $Ctx.Requirements --disable-pip-version-check
    return ($LASTEXITCODE -eq 0)
}

function Invoke-PackageTests {
    param([string]$PythonExe)
    if ($SkipTests) {
        Write-Warn "테스트를 건너뜁니다."
        return $true
    }
    Write-Step "패키지 검증 테스트"
    & $PythonExe -m compileall -q $Ctx.Root
    if ($LASTEXITCODE -ne 0) { return $false }
    & $PythonExe (Join-Path $Ctx.Root "test_app.py")
    return ($LASTEXITCODE -eq 0)
}

function Build-Exe {
    param([string]$PythonExe)
    Write-Step "Windows exe 빌드"
    foreach ($dir in @((Join-Path $Ctx.Root "build"), (Join-Path $Ctx.Root "dist"))) {
        if (Test-Path $dir) { Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue }
    }
    & $PythonExe -m PyInstaller --noconfirm --clean $Ctx.SpecFile
    if ($LASTEXITCODE -ne 0) { return $null }
    if (-not (Test-Path $Ctx.DistExe)) { return $null }
    $sizeMb = [Math]::Round(((Get-Item $Ctx.DistExe).Length / 1MB), 1)
    Write-Ok "빌드 완료: $($Ctx.DistExe) ($sizeMb MB)"
    return $Ctx.DistExe
}

function New-Shortcut {
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
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($ShortcutPath)
        $shortcut.TargetPath = $TargetPath
        $shortcut.WorkingDirectory = $WorkingDirectory
        if ($Arguments) { $shortcut.Arguments = $Arguments }
        if ($IconLocation) { $shortcut.IconLocation = $IconLocation }
        $shortcut.Save()
        return $true
    } catch {
        $cmdPath = [System.IO.Path]::ChangeExtension($ShortcutPath, ".cmd")
        $body = "@echo off`r`nchcp 65001 >nul`r`ncd /d `"$WorkingDirectory`"`r`nstart `"`" `"$TargetPath`" $Arguments`r`n"
        Write-PlainText -Path $cmdPath -Content $body
        Write-Warn "바로가기 생성이 막혀 cmd 런처로 대체했습니다: $cmdPath"
        return (Test-Path $cmdPath)
    }
}

function Stop-ExistingApp {
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            ($_.ProcessName -like "*하태욱*") -or
            ($_.Path -and $_.Path -like "*$($Ctx.AppDirName)*")
        } |
        Stop-Process -Force -ErrorAction SilentlyContinue
}

function Install-Exe {
    param([string]$ExePath)
    Write-Step "프로그램 설치"
    Stop-ExistingApp
    if (-not (Test-Path $Ctx.InstallDir)) {
        New-Item -ItemType Directory -Path $Ctx.InstallDir -Force | Out-Null
    }
    Copy-Item -Path $ExePath -Destination $Ctx.InstalledExe -Force
    $icon = "$($Ctx.InstalledExe),0"
    New-Shortcut -TargetPath $Ctx.InstalledExe -ShortcutPath $Ctx.StartMenuLink `
        -WorkingDirectory $Ctx.InstallDir -IconLocation $icon | Out-Null
    if (-not $NoDesktopShortcut) {
        New-Shortcut -TargetPath $Ctx.InstalledExe -ShortcutPath $Ctx.DesktopLink `
            -WorkingDirectory $Ctx.InstallDir -IconLocation $icon | Out-Null
    }
    Write-Ok "설치 완료: $($Ctx.InstalledExe)"
}

function Register-Autostart {
    param([string]$TargetPath, [string]$WorkingDirectory)
    if ($NoAutoStart) {
        Write-Warn "자동 시작 등록을 건너뜁니다."
        return
    }
    Write-Step "Windows 자동 시작 등록"
    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    New-Item -Path $runKey -Force | Out-Null
    Set-ItemProperty -Path $runKey -Name $Ctx.AppDirName -Value "`"$TargetPath`" --background" -Force
    Write-Ok "Run 키 등록 완료"

    try {
        $action = New-ScheduledTaskAction -Execute $TargetPath -Argument "--background" -WorkingDirectory $WorkingDirectory
        $trigger = New-ScheduledTaskTrigger -AtLogOn
        $principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel LeastPrivilege
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
        Register-ScheduledTask -TaskName $Ctx.TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
        Write-Ok "작업 스케줄러 등록 완료"
    } catch {
        Write-Warn "작업 스케줄러 등록 실패. Run 키 자동 시작은 이미 등록되었습니다. $_"
    }
}

function Install-SourceFallback {
    param([string]$PythonExe)
    Write-Warn "exe 빌드가 실패해 소스 실행 방식으로 설치합니다."
    Stop-ExistingApp
    if (-not (Test-Path $Ctx.InstallDir)) {
        New-Item -ItemType Directory -Path $Ctx.InstallDir -Force | Out-Null
    }
    Copy-Item -Path (Join-Path $Ctx.Root "*.py") -Destination $Ctx.InstallDir -Force
    Copy-Item -Path $Ctx.AssetsDir -Destination $Ctx.InstallDir -Recurse -Force
    $runtimeDir = Join-Path $Ctx.InstallDir "runtime"
    if (Test-Path $runtimeDir) {
        Remove-Item -Recurse -Force $runtimeDir -ErrorAction SilentlyContinue
    }
    Copy-Item -Path $Ctx.VenvDir -Destination $runtimeDir -Recurse -Force
    $runtimePython = Join-Path $runtimeDir "Scripts\pythonw.exe"
    if (-not (Test-Path $runtimePython)) {
        $runtimePython = Join-Path $runtimeDir "Scripts\python.exe"
    }
    if (-not (Test-Path $runtimePython)) {
        $runtimePython = $PythonExe
    }
    $runBat = @"
@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "$runtimePython" "%~dp0main.py" %*
"@
    Write-PlainText -Path $Ctx.InstalledRunBat -Content $runBat
    New-Shortcut -TargetPath $Ctx.InstalledRunBat -ShortcutPath $Ctx.StartMenuLink `
        -WorkingDirectory $Ctx.InstallDir | Out-Null
    if (-not $NoDesktopShortcut) {
        New-Shortcut -TargetPath $Ctx.InstalledRunBat -ShortcutPath $Ctx.DesktopLink `
            -WorkingDirectory $Ctx.InstallDir | Out-Null
    }
    Register-Autostart -TargetPath $Ctx.InstalledRunBat -WorkingDirectory $Ctx.InstallDir
    Write-Ok "소스 실행 방식 설치 완료: $($Ctx.InstalledRunBat)"
}

function Get-ExistingExe {
    if (Test-Path $Ctx.DistExe) { return $Ctx.DistExe }
    if (Test-Path $Ctx.PrebuiltExe) { return $Ctx.PrebuiltExe }
    return $null
}

Initialize-Log
Show-Banner
Write-Info "작업 폴더: $($Ctx.Root)"
Write-Info "로그 파일: $($Ctx.LogFile)"

if (-not (Test-Windows)) {
    Write-Fail "이 스크립트는 Windows에서 실행해야 합니다. macOS에서는 Windows exe를 직접 빌드할 수 없습니다."
    Pause-End 1
}

Invoke-SafePathRerun

if (-not (Test-RequiredFiles)) { Pause-End 1 }

try {
    $existingExe = Get-ExistingExe
    if ($InstallOnly -or ($PreferExistingExe -and $existingExe)) {
        if (-not $existingExe) {
            Write-Fail "설치할 기존 exe가 없습니다. 먼저 빌드하거나 prebuilt 폴더에 exe를 넣으세요."
            Pause-End 1
        }
        if ($BuildOnly) {
            Write-Ok "기존 exe 확인: $existingExe"
            Pause-End 0
        }
        Install-Exe -ExePath $existingExe
        Register-Autostart -TargetPath $Ctx.InstalledExe -WorkingDirectory $Ctx.InstallDir
        Pause-End 0
    }

    $python = Find-Python
    if (-not $python) {
        Write-Warn "Python 3.10+를 찾지 못했습니다."
        $python = Install-PythonForUser
    }
    if (-not $python) {
        $existingExe = Get-ExistingExe
        if ($existingExe -and -not $BuildOnly) {
            Write-Warn "Python 설치가 실패했지만 기존 exe를 설치합니다: $existingExe"
            Install-Exe -ExePath $existingExe
            Register-Autostart -TargetPath $Ctx.InstalledExe -WorkingDirectory $Ctx.InstallDir
            Pause-End 0
        }
        Write-Fail "Python 준비 실패. 인터넷 연결을 확인하거나 prebuilt 폴더에 미리 빌드한 exe를 넣으세요."
        Pause-End 1
    }
    Write-Ok "Python 사용: $python"

    $venvPython = New-BuildVenv -PythonExe $python
    if (-not (Install-Packages -PythonExe $venvPython)) {
        Write-Fail "패키지 설치 실패"
        Pause-End 1
    }
    Write-Ok "패키지 설치 완료"

    if (-not (Invoke-PackageTests -PythonExe $venvPython)) {
        Write-Fail "검증 테스트 실패"
        Pause-End 1
    }
    Write-Ok "검증 테스트 통과"

    $builtExe = Build-Exe -PythonExe $venvPython
    if (-not $builtExe) {
        if ($BuildOnly) {
            Write-Fail "exe 빌드 실패"
            Pause-End 1
        }
        Install-SourceFallback -PythonExe $venvPython
        Pause-End 0
    }

    if ($BuildOnly) {
        Write-Ok "빌드만 완료했습니다: $builtExe"
        Pause-End 0
    }

    Install-Exe -ExePath $builtExe
    Register-Autostart -TargetPath $Ctx.InstalledExe -WorkingDirectory $Ctx.InstallDir
    Write-Ok "최종 완료"
    Write-Info "실행 파일: $builtExe"
    Write-Info "설치 위치: $($Ctx.InstallDir)"
    Pause-End 0
} catch {
    Write-Fail "처리 중 오류: $_"
    Pause-End 1
}
