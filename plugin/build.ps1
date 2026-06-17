# Build the Keel plugin spike (VST3 + Standalone).
#
#   .\build.ps1            # configure (if needed) + Release build
#   .\build.ps1 -Debug     # Debug build
#   .\build.ps1 -Clean     # wipe the build dir first
#
# Requires: CMake >= 3.22, Visual Studio 2026 (MSVC), git, and internet on the
# first run (CMake FetchContent pulls JUCE 8.0.9). See ADR-0026.

param(
    [switch]$Debug,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$buildDir = Join-Path $here "build"
$config = if ($Debug) { "Debug" } else { "Release" }

if ($Clean -and (Test-Path $buildDir)) {
    Write-Host "Cleaning $buildDir" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir
}

if (-not (Test-Path (Join-Path $buildDir "CMakeCache.txt"))) {
    Write-Host "Configuring (CMake will fetch JUCE 8.0.9 on first run)..." -ForegroundColor Cyan
    cmake -S $here -B $buildDir -G "Visual Studio 18 2026" -A x64
    if ($LASTEXITCODE -ne 0) { throw "CMake configure failed" }
}

Write-Host "Building ($config)..." -ForegroundColor Cyan
cmake --build $buildDir --config $config
if ($LASTEXITCODE -ne 0) { throw "Build failed" }

Write-Host "Done. Artifacts under:" -ForegroundColor Green
Write-Host "  $buildDir\KeelPlugin_artefacts\$config\VST3\Keel.vst3"
Write-Host "  $buildDir\KeelPlugin_artefacts\$config\Standalone\Keel.exe"
