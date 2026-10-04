param(
    [string]$RuntimeSource = "",
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Dist = Join-Path $Root "dist"
$VersionFile = Join-Path $Root "rhodes\__init__.py"

function Pause-IfNeeded {
    if (-not $NoPause) {
        Write-Host ""
        Read-Host "Press Enter to close"
    }
}

function Fail-Build {
    param([string]$Message)
    Write-Host ""
    Write-Host "BUILD FAILED" -ForegroundColor Red
    Write-Host $Message -ForegroundColor Red
    Pause-IfNeeded
    exit 1
}

trap {
    Write-Host ""
    Write-Host "BUILD FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Pause-IfNeeded
    exit 1
}

if (-not (Test-Path $VersionFile)) {
    Fail-Build "Version file not found: $VersionFile"
}

$VersionText = Get-Content $VersionFile -Raw
$VersionMatch = [regex]::Match($VersionText, '__version__\s*=\s*["'']([^"'']+)["'']')
if (-not $VersionMatch.Success) {
    Fail-Build "Could not read __version__ from $VersionFile"
}
$Version = $VersionMatch.Groups[1].Value

$PackageName = "RhodesPlanner-v$Version-portable-windows-x64"
$PackageDir = Join-Path $Dist $PackageName
$ZipPath = Join-Path $Dist ($PackageName + ".zip")

# ---------------------------------------------------------------------------
# Locate a usable portable Python runtime.
#
# Priority:
# 1. -RuntimeSource argument
# 2. runtime\ beside this build script
# 3. exactly one sibling folder containing runtime\python.exe
#
# The sibling folder itself can have ANY name.
# ---------------------------------------------------------------------------

$RuntimeDir = $null

if ($RuntimeSource) {
    $candidate = [System.IO.Path]::GetFullPath($RuntimeSource)

    if ((Test-Path $candidate -PathType Leaf) -and
        ([System.IO.Path]::GetFileName($candidate) -ieq "python.exe")) {
        $candidate = Split-Path -Parent $candidate
    }

    if (Test-Path (Join-Path $candidate "python.exe")) {
        $RuntimeDir = $candidate
    }
    elseif (Test-Path (Join-Path $candidate "runtime\python.exe")) {
        $RuntimeDir = Join-Path $candidate "runtime"
    }
    else {
        Fail-Build "RuntimeSource does not contain python.exe or runtime\python.exe: $RuntimeSource"
    }
}

if (-not $RuntimeDir) {
    $localRuntime = Join-Path $Root "runtime"
    if (Test-Path (Join-Path $localRuntime "python.exe")) {
        $RuntimeDir = $localRuntime
    }
}

if (-not $RuntimeDir) {
    $Parent = Split-Path -Parent $Root
    $matches = @()

    Get-ChildItem -Path $Parent -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $candidateRuntime = Join-Path $_.FullName "runtime"
        if (Test-Path (Join-Path $candidateRuntime "python.exe")) {
            $matches += $candidateRuntime
        }
    }

    if ($matches.Count -eq 1) {
        $RuntimeDir = $matches[0]
        Write-Host "Auto-detected portable runtime:" -ForegroundColor Yellow
        Write-Host $RuntimeDir
    }
    elseif ($matches.Count -gt 1) {
        Write-Host ""
        Write-Host "Multiple portable runtimes were found:" -ForegroundColor Yellow
        $matches | ForEach-Object { Write-Host "  $_" }
        Fail-Build "Run the script with -RuntimeSource to select the correct portable folder/runtime."
    }
}

if (-not $RuntimeDir) {
    Write-Host ""
    Write-Host "No portable runtime was found." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Put the extracted source folder beside your existing portable folder,"
    Write-Host "or run:"
    Write-Host ""
    Write-Host '  .\build_portable_release.ps1 -RuntimeSource "C:\path\to\your\portable"' -ForegroundColor Cyan
    Write-Host ""
    Write-Host "The portable folder may have ANY name."
    Fail-Build "A Python runtime is required to build the standalone portable release."
}

$RuntimePython = Join-Path $RuntimeDir "python.exe"

Write-Host ""
Write-Host "=== Rhodes Planner Portable Builder ===" -ForegroundColor Cyan
Write-Host "Source : $Root"
Write-Host "Version: $Version"
Write-Host "Runtime: $RuntimeDir"
Write-Host "Output : $ZipPath"
Write-Host ""

if (Test-Path $PackageDir) {
    Remove-Item $PackageDir -Recurse -Force
}
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
New-Item -ItemType Directory -Path $PackageDir -Force | Out-Null

# Copy runtime independently from application source.
Write-Host "Copying portable runtime..." -ForegroundColor Cyan
Copy-Item $RuntimeDir (Join-Path $PackageDir "runtime") -Recurse -Force

# Copy application folders from the source tree.
$folders = @("app", "rhodes", ".streamlit")
foreach ($folder in $folders) {
    $src = Join-Path $Root $folder
    if (-not (Test-Path $src)) {
        Fail-Build "Required source folder missing: $src"
    }
    Copy-Item $src $PackageDir -Recurse -Force
}

$files = @(
    "Rhodes Planner.bat",
    "requirements.txt",
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CREDITS.md",
    "THIRD_PARTY_NOTICES.md",
    "RELEASE_NOTES.md"
)

foreach ($file in $files) {
    $src = Join-Path $Root $file
    if (Test-Path $src) {
        Copy-Item $src $PackageDir -Force
    }
}

# Strip disposable Python cache files from the release.
Get-ChildItem $PackageDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $PackageDir -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

$PackagedPython = Join-Path $PackageDir "runtime\python.exe"

Write-Host "Checking bundled Python..." -ForegroundColor Cyan
& $PackagedPython -c "import streamlit, pandas, pydantic, requests, platformdirs; print('Portable runtime OK')"
if ($LASTEXITCODE -ne 0) {
    Fail-Build "Portable runtime validation failed."
}

Write-Host "Checking launcher syntax..." -ForegroundColor Cyan
$Launcher = Join-Path $PackageDir "app\launcher.py"
if (-not (Test-Path $Launcher)) {
    Fail-Build "Launcher missing from packaged application: $Launcher"
}
& $PackagedPython -m py_compile $Launcher
if ($LASTEXITCODE -ne 0) {
    Fail-Build "Launcher validation failed."
}

Write-Host "Creating ZIP..." -ForegroundColor Cyan
Compress-Archive `
    -Path (Join-Path $PackageDir "*") `
    -DestinationPath $ZipPath `
    -CompressionLevel Optimal

if (-not (Test-Path $ZipPath)) {
    Fail-Build "ZIP creation reported success but the ZIP was not found."
}

$ZipSizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)

Write-Host ""
Write-Host "BUILD SUCCESSFUL" -ForegroundColor Green
Write-Host "Portable folder:"
Write-Host $PackageDir
Write-Host ""
Write-Host "Release ZIP:"
Write-Host $ZipPath
Write-Host "Size: $ZipSizeMB MB"

Pause-IfNeeded
