# vendor/ — offline copies of the engine's dependencies

These `.whl` files are the exact wheels Keel needs, saved locally so the tool can
be reinstalled **with no internet** — insurance in case any of these get pulled
from PyPI (e.g. Spotify removing pedalboard).

## Install offline from here

Core engine (the internal mix + master path, always needed):

```powershell
python -m pip install --no-index --find-links vendor numpy scipy soundfile pyloudnorm pedalboard
```

Optional reference-master path (Matchering) — pulls a heavy numba / llvmlite /
pandas tree, so only install it if you want the reference-matched master:

```powershell
python -m pip install --no-index --find-links vendor matchering
```

`--no-index` = don't touch PyPI; `--find-links vendor` = install only from these
files. Either command resolves entirely from this folder, offline.

## What's here (pinned versions)

Core:

| package | version | why |
|---|---|---|
| numpy | 2.4.6 | math core |
| scipy | 1.17.1 | polyphase-FIR oversampling (true-peak meter + soft-clip/limiter); also pyloudnorm's filters |
| soundfile | 0.14.0 | WAV/FLAC I/O |
| pyloudnorm | 0.2.0 | LUFS metering |
| pedalboard | 0.9.23 | effects + limiter (Spotify) |
| cffi / pycparser / typing_extensions | — | sub-deps of the above |

Optional (Matchering reference-master path):

| package | version | why |
|---|---|---|
| matchering | 2.0.6 | reference-matched mastering |
| numba | 0.65.1 | JIT used by resampy |
| llvmlite | 0.47.0 | numba's LLVM backend (~37 MB) |
| resampy | 0.4.3 | high-quality resampling |
| pandas / statsmodels / patsy | 3.0.3 / 0.14.6 / 1.0.2 | matchering's analysis stack |
| python-dateutil / six / tzdata / packaging | — | sub-deps of the above |

## Platform note

These are **Windows 64-bit, CPython 3.14** wheels (`cp314-win_amd64`), matching
this machine. On a different OS or Python version they won't install — re-vendor
with:

```powershell
python -m pip download numpy scipy soundfile pyloudnorm pedalboard -d vendor
python -m pip download matchering -d vendor   # optional reference-master path
```
