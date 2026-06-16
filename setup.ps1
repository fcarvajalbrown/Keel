# setup.ps1 — create a local virtual environment for Keel and install its deps.
#
# A venv keeps Keel's dependencies isolated from the system Python, so the engine
# runs the same on any machine. The venv itself is NOT committed (it is machine-
# and platform-specific); this script rebuilds it from requirements.txt / vendor.
#
#   .\setup.ps1                 # create .venv, install the core engine OFFLINE from vendor/
#   .\setup.ps1 -Online         # same, but pull from PyPI instead of vendor/
#   .\setup.ps1 -Matchering     # also install the optional reference-master path
#   .\setup.ps1 -Gui            # also install PySide6 for the desktop GUI (online only)
#
# After it finishes, activate the venv with:
#   .\.venv\Scripts\Activate.ps1
param(
    [switch]$Online,      # install from PyPI instead of the offline vendor/ wheels
    [switch]$Matchering,  # also install the optional reference-master dependency
    [switch]$Gui          # also install PySide6 (the GUI front-end; PyPI, not vendored)
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venv = Join-Path $root ".venv"
$py   = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "Creating virtual environment in .venv ..."
    python -m venv $venv
}

$core = @("numpy", "scipy", "soundfile", "pyloudnorm", "pedalboard")
if ($Online) {
    Write-Host "Installing core engine from PyPI ..."
    & $py -m pip install @core
} else {
    Write-Host "Installing core engine OFFLINE from vendor/ ..."
    & $py -m pip install --no-index --find-links (Join-Path $root "vendor") @core
}

if ($Matchering) {
    if ($Online) {
        Write-Host "Installing optional matchering from PyPI ..."
        & $py -m pip install matchering
    } else {
        Write-Host "Installing optional matchering OFFLINE from vendor/ ..."
        & $py -m pip install --no-index --find-links (Join-Path $root "vendor") matchering
    }
}

if ($Gui) {
    # PySide6 is the desktop GUI's only extra dep. It ships a large (~150 MB) set
    # of Qt binaries, so it is NOT vendored offline (that would bloat the repo) --
    # the GUI is an online-install opt-in, while the core engine stays offline.
    Write-Host "Installing PySide6 (GUI) from PyPI ..."
    & $py -m pip install PySide6
}

Write-Host ""
Write-Host "Done. Activate the venv with:"
Write-Host "    .\.venv\Scripts\Activate.ps1"
Write-Host "Then run, e.g.:"
Write-Host "    python build.py --stems `"C:\path\to\stems`" --out out"
if ($Gui) {
    Write-Host "Or launch the desktop GUI:"
    Write-Host "    python gui.py"
}
