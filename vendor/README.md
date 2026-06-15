# vendor/ — offline copies of the engine's dependencies

These `.whl` files are the exact wheels the automix/automaster engine needs,
saved locally so the tool can be reinstalled **with no internet** — insurance in
case any of these get pulled from PyPI (e.g. Spotify removing pedalboard).

## Install offline from here

```powershell
cd src
python -m pip install --no-index --find-links vendor numpy scipy soundfile pyloudnorm pedalboard
```

`--no-index` = don't touch PyPI; `--find-links vendor` = install only from these
files. That covers the **internal master path** (the one in use). Matchering (the
optional reference-master path) is NOT vendored — install it online if you ever
want it.

## What's here (pinned versions)

| package | version | why |
|---|---|---|
| numpy | 2.4.6 | math core |
| scipy | 1.17.1 | polyphase-FIR oversampling (true-peak meter + soft-clip/limiter); also pyloudnorm's filters |
| soundfile | 0.14.0 | WAV/FLAC I/O |
| pyloudnorm | 0.2.0 | LUFS metering |
| pedalboard | 0.9.23 | effects + limiter (Spotify) |
| cffi / pycparser / typing_extensions | — | sub-deps of the above |

## Platform note

These are **Windows 64-bit, CPython 3.14** wheels (`cp314-win_amd64`), matching
this machine. On a different OS or Python version they won't install — re-vendor
with `python -m pip download numpy soundfile pyloudnorm pedalboard -d vendor`.
