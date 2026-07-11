# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
"""
build.py  —  Keel's command-line button (orchestrator).

Point it at a folder of finished, FX-printed stems and it renders a balanced
stereo mix and a loudness-safe master:

    out/<name>_mix.wav      out/<name>_master.wav

LABELING (any number of stems). Keel does NOT assume a fixed set of stem types.
On the first run over a folder it AUTO-DETECTS a label for every audio file
(from its filename) and writes an editable mapping, `keel.json`, into that
folder:

    {
      "stems":   { "kick.wav": "drums", "gtr_DI_1.wav": "guitar", ... },
      "balance": { "vocals": 0.0, "drums": -2.0, "guitar": -3.5, ... },
      "pan":     {},               # label -> -1.0 (L) .. +1.0 (R)
      "spread":  {},               # label -> 0..1 auto-spread multi-file groups
      "glue":    false,            # gentle bus-glue compressor (off by default)
      "master":  { "target_lufs": -14.0, "tp_ceiling_db": -1.0, "reference": null }
    }

Edit the labels (assign guitar/bass/vocals/... to each file — a label can hold 1
or 10 files) and the per-label balance, then re-run to apply. Files sharing a
label are balanced as one group. Auto-detect is only a starting guess; the
mapping is the source of truth.

MODES:
  SINGLE  (default) — one folder of stems:
      python build.py --stems "C:\\path\\to\\stems" --out out
      python build.py --stems ./stems --scan         # only (re)write keel.json
      python build.py --stems ./stems --map my.json  # use a mapping elsewhere
  BATCH — every immediate subfolder that contains stems:
      python build.py --batch "C:\\path\\to\\album" --out out
      python build.py --batch ./album --album   # one shared album gain, relative
                                                 # track loudness preserved

STAGE / MASTER controls:
      --mix-only / --master-only          stop after mix / remaster existing mix
      --glue / --no-glue                  force the bus-glue compressor on/off
      --preset loud                       house-sound loudness profile (see below)
      --lufs -11 --tp -1                  override the mapping's master target
      --targets streaming,-16,loud        one master PER target, each re-run at-spec
      --auto-tp                           key the TP ceiling to loudness (-14->-1,
                                          -9->-2 dBTP); --tp still overrides it
      --bit-depth 16 --dither tpdf        export word length + seeded dither
                                          (dither when going sub-32-bit, e.g. 16)
      --format flac,mp3                   also transcode the master to these
                                          delivery formats (FLAC/MP3/OGG/AAC)
      --ref "C:\\refs\\master.wav"         match a reference (ignores --lufs)
      --match-loudness "C:\\refs\\a.wav"   match a reference's LOUDNESS only
                                          (deterministic, no ML; beaten by --lufs)

PRESETS (named master loudness profiles, applied live at render — they override
the mapping's master block; an explicit --lufs/--tp still wins). `--list-presets`
prints them. Built in: streaming (-14 LUFS, the default normalization target),
loud (-10), broadcast (-16). All at a -1.0 dBTP ceiling.

Deterministic: same stems + same mapping + same options -> identical output.
A QC sheet is written to <out>/REPORT.md after every render.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

import recipes
import mixer
import mastering
import meters
import encode

MAPPING_NAME = "keel.json"


class _ListPresets(argparse.Action):
    """`--list-presets`: print the named loudness profiles and exit (before the
    --stems/--batch requirement is enforced, so it works on its own)."""
    def __init__(self, option_strings, dest, **kw):
        super().__init__(option_strings, dest, nargs=0, **kw)

    def __call__(self, parser, namespace, values, option_string=None):
        print("Presets (master loudness target / true-peak ceiling):")
        for nm in sorted(recipes.PRESETS):
            m = recipes.PRESETS[nm]
            dflt = "  (default)" if nm == recipes.DEFAULT_PRESET else ""
            print(f"  {nm:<10} {m['target_lufs']:>6} LUFS / "
                  f"{m['tp_ceiling_db']:>5} dBTP{dflt}")
        parser.exit()


def _resolve_ref(ref):
    """Split a --ref path into (references_dir, filename) for mastering.master."""
    if not ref:
        return None, None
    p = Path(ref).expanduser().resolve()
    return p.parent, p.name


def mapping_path(stems_dir, explicit=None):
    return Path(explicit) if explicit else Path(stems_dir) / MAPPING_NAME


def build_mapping_doc(stems_dir):
    """Auto-detect labels for every file and seed an editable mapping document:
    file->label plus per-label balance seeded from recipes.DEFAULT_BALANCE
    (unknown labels default to 0.0), and the default master target."""
    fmap = mixer.autodetect(stems_dir)
    labels = list(dict.fromkeys(fmap.values()))  # ordered, unique
    balance = {lb: recipes.DEFAULT_BALANCE.get(lb, 0.0) for lb in labels}
    return {
        "stems": fmap,
        "balance": balance,
        "pan": {},
        "spread": {},
        "glue": False,   # gentle bus-glue compressor; OFF (stems are mix-ready)
        "auto_tp": False,  # key the true-peak ceiling to loudness; OFF (fixed -1)
        "master": {
            "target_lufs": recipes.DEFAULT_MASTER["target_lufs"],
            "tp_ceiling_db": recipes.DEFAULT_MASTER["tp_ceiling_db"],
            "reference": None,
        },
    }


def _print_mapping_review(mpath, doc):
    """Dry-run summary of an auto-detected mapping: every label with its file
    count and files, so the user can spot a mislabel before rendering. Files that
    matched no alias (OTHER_LABEL) are called out explicitly — that's where a
    silently mis-detected stem would hide."""
    stems = doc["stems"]
    by_label = {}
    for fn, lb in stems.items():
        by_label.setdefault(lb, []).append(fn)
    print(f"  mapping -> {mpath}  ({len(stems)} files, "
          f"{len(by_label)} labels)")
    for lb, files in by_label.items():
        head = ", ".join(files[:4]) + (" ..." if len(files) > 4 else "")
        print(f"      {lb:<8} x{len(files):<3} {head}")
    other = by_label.get(mixer.OTHER_LABEL, [])
    if other:
        print(f"  [check] {len(other)} file(s) matched no label -> "
              f"'{mixer.OTHER_LABEL}' (balance 0.0): {', '.join(other)}")
        print(f"          reassign them in {Path(mpath).name} if that's wrong.")
    print(f"  edit labels/balance in {Path(mpath).name} and re-run to refine.")


def load_mapping_doc(path):
    """Read a keel.json mapping. A hand-edit that breaks the JSON raises a clear,
    user-facing error (never a raw JSONDecodeError) and the file is left untouched
    so the user's edits aren't lost — fix the typo, or delete keel.json to let
    Keel re-detect labels from the filenames."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"{Path(path)} is not valid JSON ({e.msg}, line {e.lineno} "
            f"col {e.colno}). Fix the typo, or delete the file to let Keel "
            f"re-detect labels."
        ) from e


def write_mapping_doc(path, doc):
    Path(path).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _parse_targets(spec):
    """Parse a '--targets streaming,-16,loud' spec into a list mixing preset NAMES
    (str) and LUFS numbers (float). A preset name is validated here (raises
    ValueError naming the valid presets on a typo)."""
    out = []
    for raw in spec.split(","):
        s = raw.strip()
        if not s:
            continue
        try:
            out.append(float(s))
        except ValueError:
            recipes.preset_master(s)   # validate the preset name (raises)
            out.append(s)
    return out


def _resolve_master_targets(targets, preset, target_lufs):
    """Plan the master renders: return [(filename_suffix, master_override), ...].

    Default (no --targets): a single render on the preset/--lufs path (suffix ""),
    so `<name>_master.wav` is written exactly as before. With --targets, one
    render per target — each a preset NAME or a LUFS number — carrying a labelled
    suffix so the files don't collide (`_streaming`, `_-16LUFS`, ...)."""
    if not targets:
        ov = {}
        if preset:
            ov.update(recipes.preset_master(preset))
        if target_lufs is not None:
            ov["target_lufs"] = target_lufs
        return [("", ov)]
    specs = []
    for tg in targets:
        if isinstance(tg, str):                      # a preset name
            specs.append((f"_{tg}", recipes.preset_master(tg)))
        else:                                        # a LUFS number
            specs.append((f"_{tg:g}LUFS", {"target_lufs": float(tg)}))
    return specs


def process_one(stems_dir, out_dir, name, *, map_file=None, scan=False,
                preset=None, target_lufs=None, tp_ceiling=None, ref=None,
                glue=None, auto_tp=None, bit_depth=24, dither=None, dither_seed=0,
                formats=None, targets=None, do_mix=True, do_master=True):
    """Mix and/or master one folder of stems via its keel.json mapping. Returns a
    REPORT.md row dict, or None if it was skipped."""
    stems_dir = Path(stems_dir)
    out_dir = Path(out_dir)
    mpath = mapping_path(stems_dir, map_file)

    # resolve the mapping document: regenerate on --scan or when absent
    if scan or not mpath.exists():
        doc = build_mapping_doc(stems_dir)
        if not doc["stems"]:
            print(f"  [skip] no audio files in {stems_dir}")
            return None
        write_mapping_doc(mpath, doc)
        _print_mapping_review(mpath, doc)
        if scan:
            return None  # --scan only writes the mapping
    else:
        doc = load_mapping_doc(mpath)

    out_dir.mkdir(parents=True, exist_ok=True)
    mix_wav = out_dir / f"{name}_mix.wav"
    print(f"=== {name} ===")
    row = {"slug": name, "mix": None, "master": None}

    mix_ov = {"balance": doc.get("balance", {}), "pan": doc.get("pan", {}),
              "spread": doc.get("spread", {}), "chain": doc.get("chain", {})}

    if do_mix:
        # glue: CLI --glue/--no-glue (True/False) overrides the mapping's "glue"
        use_glue = doc.get("glue", False) if glue is None else glue
        try:
            rep = mixer.mix(stems_dir, recipes.mix_recipe(mix_ov), mix_wav,
                            mapping=doc.get("stems"), glue=use_glue)
        except FileNotFoundError as e:
            print(f"  [skip] {e}")
            return None
        row["mix"] = rep
        gtag = "  glue:on" if use_glue else ""
        print(f"  mix    -> {rep['out']}  {rep['seconds']}s "
              f"{rep['peak_dbfs']} dBFS  groups: {', '.join(rep['groups'])}{gtag}")

    if do_master:
        if not mix_wav.exists():
            print(f"  [skip master] no mix at {mix_wav}")
            return row if row["mix"] else None
        base = dict(doc.get("master", {}))
        eff_auto_tp = doc.get("auto_tp", False) if auto_tp is None else auto_tp
        refs_dir, ref_name = _resolve_ref(ref)
        dtag = (f"  {bit_depth}-bit/{dither}" if dither
                else (f"  {bit_depth}-bit" if bit_depth != 24 else ""))

        # One render per requested target (default: a single render on the
        # preset/--lufs path). Each target re-runs the whole chain so every file
        # is genuinely at-spec — a stereo master can't be re-normalized after the
        # fact without breaking the true-peak guarantee (ADR-0001).
        masters = []
        for suffix, tgt_ov in _resolve_master_targets(targets, preset, target_lufs):
            m_ov = dict(base)
            m_ov.update(tgt_ov)
            # true-peak ceiling precedence: explicit --tp wins; else auto-tp keyed
            # to THIS target's loudness; else the preset/keel.json ceiling stands.
            if tp_ceiling is not None:
                m_ov["tp_ceiling_db"] = tp_ceiling
            elif eff_auto_tp:
                tgt = m_ov.get("target_lufs", recipes.DEFAULT_MASTER["target_lufs"])
                m_ov["tp_ceiling_db"] = recipes.tp_ceiling_for_lufs(tgt)
            if ref_name:  # a reference dictates loudness -> targets don't apply
                m_ov["reference"] = ref_name
            recipe = recipes.master_recipe(m_ov)
            mwav = out_dir / f"{name}_master{suffix}.wav"
            rep = mastering.master(mix_wav, recipe, mwav,
                                   references_dir=refs_dir, bit_depth=bit_depth,
                                   dither=dither, dither_seed=dither_seed)
            # keep the requested target for the report (rep['lufs'] is measured)
            rep["target_lufs_req"] = recipe.get("target_lufs")
            stamp = rep.get("compliance", {}).get("verdict", "")
            ttag = f"  target:{recipe.get('target_lufs')}" if suffix else ""
            print(f"  master -> {rep['out']}  [{rep['path']}]  "
                  f"{rep['lufs']} LUFS  {rep['true_peak_db']} dBTP  "
                  f"{stamp}{dtag}{ttag}")

            # transcode this master into the extra delivery formats (no DSP re-run
            # — the master WAV is the single source for every format).
            if formats:
                enc = encode.export(mwav, formats, out_dir,
                                    f"{name}_master{suffix}",
                                    tp_ceiling_db=recipe.get("tp_ceiling_db"))
                rep["encoded"] = enc
                for e in enc:
                    kb = round(e["bytes"] / 1024)
                    tag = "lossless" if e["lossless"] else "lossy"
                    v = e.get("tp_verify")
                    vtag = (f"  post-TP {v['post_tp_db']} dBTP {v['verdict']}"
                            if v else "")
                    print(f"  encode -> {e['out']}  [{e['format']}, {tag}, "
                          f"{kb} KB]{vtag}")
            masters.append(rep)

        row["masters"] = masters
        row["master"] = masters[0]                       # back-compat (primary)
        row["target_lufs"] = masters[0].get("target_lufs_req")

    return row if (row["mix"] or row.get("master")) else None


def discover_batch(parent):
    """Immediate subfolders of `parent` that hold at least one audio file, each a
    project named after the subfolder."""
    parent = Path(parent)
    jobs = []
    for sub in sorted(p for p in parent.iterdir() if p.is_dir()):
        if mixer.autodetect(sub):
            jobs.append((sub, sub.name))
    return jobs


def _compliance_line(comp, ms):
    """Render the per-check PASS/FAIL detail behind a master's compliance stamp:
    the loudness-vs-target check (skipped on the reference path, where the
    reference sets loudness) and the true-peak-ceiling check."""
    parts = []
    if comp.get("lufs_ok") is not None:
        tag = "ok" if comp["lufs_ok"] else "OFF"
        parts.append(f"loudness {ms['lufs']} within +/-{comp['lufs_tol']} LU of "
                     f"{comp['target_lufs']} [{tag}]")
    tp_tag = "ok" if comp.get("tp_ok") else "OVER"
    parts.append(f"true-peak {ms['true_peak_db']} <= {comp['tp_ceiling_db']} dBTP "
                 f"[{tp_tag}]")
    return " | ".join(parts)


def _master_report_lines(ms, labelled=False):
    """Render one master's QC block: loudness/true-peak vs. target with the
    PASS/FAIL stamp, the PLR/PSR + phase-correlation meters, the per-check detail,
    and any encoded delivery formats (with their post-codec true-peak gate).
    `labelled` prefixes the target when a project rendered several (multi-target)."""
    tgt = ms.get("target_lufs_req")
    off = ("" if tgt is None or not isinstance(ms["lufs"], (int, float))
           else f"  (target {tgt}, off by {round(ms['lufs'] - tgt, 2)} LU)")
    comp = ms.get("compliance", {})
    stamp = f"  —  **{comp['verdict']}**" if comp.get("verdict") else ""
    head = f"@ {tgt} LUFS " if (labelled and tgt is not None) else ""
    lines = [f"- Master {head}[{ms['path']}]: **{ms['lufs']} LUFS**, "
             f"**{ms['true_peak_db']} dBTP**{off}{stamp}"]
    dyn = []
    if ms.get("plr") is not None:
        dyn.append(f"PLR {ms['plr']} dB")
    if ms.get("psr") is not None:
        dyn.append(f"PSR {ms['psr']} dB")
    if ms.get("correlation") is not None:
        dyn.append(f"phase corr {ms['correlation']:+.2f}")
    if dyn:
        lines.append(f"  - dynamics: {' | '.join(dyn)}")
    if comp:
        lines.append(f"  - checks: {_compliance_line(comp, ms)}")
    enc = ms.get("encoded")
    if enc:
        parts = [f"{e['format'].upper()} "
                 f"({'lossless' if e['lossless'] else 'lossy'}, "
                 f"{round(e['bytes'] / 1024)} KB)" for e in enc]
        lines.append(f"  - encoded: {', '.join(parts)}")
        verified = [e for e in enc if e.get("tp_verify")]
        if verified:
            vp = [f"{e['format'].upper()} {e['tp_verify']['post_tp_db']} dBTP "
                  f"[{e['tp_verify']['verdict']}]" for e in verified]
            lines.append(f"  - post-codec true-peak: {' | '.join(vp)}")
    return lines


def run_album(jobs, out_dir, args, formats):
    """Album loudness-consistency mode. Mix every track, measure each mix's
    loudness, then master each to a PER-TRACK target set by its offset from the
    album's integrated loudness: track_target = album_target + (track - album).

    A louder-mixed track gets a proportionally louder master and a quieter one a
    quieter master, so the intended loudness differences BETWEEN tracks survive
    (EBU R128 album normalisation) — instead of flattening every track to the same
    LUFS. Because the offsets are measured against the album mean, the album's own
    integrated loudness lands on the target while each track still runs the normal
    exact-normalize + true-peak chain (so each is precise and TP-safe).
    Returns (report, errors)."""
    out_dir = Path(out_dir)
    _suffix, tgt_ov = _resolve_master_targets(None, args.preset, args.lufs)[0]
    album_target = tgt_ov.get("target_lufs", recipes.DEFAULT_MASTER["target_lufs"])

    # pass 1 — mix every track; measure each mix's integrated loudness + duration.
    tracks, errors = [], 0
    for stems_dir, name in jobs:
        try:
            row = process_one(stems_dir, out_dir, name, map_file=args.map_file,
                              glue=args.glue, do_mix=True, do_master=False)
        except (ValueError, FileNotFoundError) as e:
            print(f"  [error] {name}: {e}")
            errors += 1
            continue
        if not row or not row.get("mix"):
            continue
        audio, rate = sf.read(str(out_dir / f"{name}_mix.wav"),
                              dtype="float32", always_2d=True)
        tracks.append({"stems": stems_dir, "name": name,
                       "lufs": meters.integrated_lufs(audio, rate),
                       "seconds": row["mix"]["seconds"], "mix": row["mix"]})
    if not tracks:
        return [], errors

    # the album's integrated loudness -> each track's offset from it.
    album_lufs = meters.album_loudness([(t["lufs"], t["seconds"]) for t in tracks])
    print(f"\n[album] {len(tracks)} tracks | album loudness "
          f"{round(album_lufs, 2)} LUFS -> target {album_target} LUFS; each "
          f"track offset by its own level so relative loudness is preserved\n")

    # pass 2 — master each track to its album-adjusted per-track target.
    report = []
    for t in tracks:
        delta = ((t["lufs"] - album_lufs)
                 if (np.isfinite(t["lufs"]) and np.isfinite(album_lufs)) else 0.0)
        track_target = round(album_target + delta, 2)
        try:
            mrow = process_one(
                t["stems"], out_dir, t["name"], map_file=args.map_file,
                target_lufs=track_target, tp_ceiling=args.tp, ref=args.ref,
                auto_tp=args.auto_tp, bit_depth=args.bit_depth, dither=args.dither,
                dither_seed=args.dither_seed, formats=formats,
                do_mix=False, do_master=True)
        except (ValueError, FileNotFoundError) as e:
            print(f"  [error] {t['name']}: {e}")
            errors += 1
            continue
        if mrow:
            mrow["mix"] = t["mix"]                 # fold pass-1 mix info back in
            mrow["album_offset"] = round(delta, 2)
            report.append(mrow)
    return report, errors


def write_report(report, out_dir):
    """One-glance QC sheet: per-project group balance (pre/post LUFS) + master
    loudness/true-peak vs. target. Written to <out>/REPORT.md."""
    L = ["# Keel — mix / master QC report",
         "",
         "Auto-generated by `build.py`. Per-project group balance and final "
         "master loudness / true-peak vs. target.",
         ""]
    for row in report:
        L.append(f"## {row['slug']}")
        L.append("")
        m = row.get("mix")
        if m:
            L.append(f"- Mix: {m['seconds']}s, bus peak {m['peak_dbfs']} dBFS, "
                     f"groups: {', '.join(m['groups'])}")
            if m.get("balance"):
                L.append("")
                L.append("| label | files | pre LUFS | gain dB | post LUFS |")
                L.append("|---|---|---|---|---|")
                for b in m["balance"]:
                    L.append(f"| {b['label']} | {b['files']} | {b['pre_lufs']} "
                             f"| {b['gain_db']} | {b['post_lufs']} |")
                L.append("")
        if row.get("album_offset") is not None:
            L.append(f"- Album offset: {row['album_offset']:+.2f} LU vs the album "
                     f"mean (relative track loudness preserved)")
        masters = row.get("masters") or ([row["master"]] if row.get("master")
                                          else [])
        multi = len(masters) > 1
        for ms in masters:
            L.extend(_master_report_lines(ms, labelled=multi))
        L.append("")
    out_path = Path(out_dir) / "REPORT.md"
    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"  report -> {out_path}")


def main(argv):
    ap = argparse.ArgumentParser(
        prog="build.py",
        description="Keel: automix + automaster a folder of finished stems.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--stems", metavar="DIR",
                     help="folder of stems to mix+master (single-project mode)")
    src.add_argument("--batch", metavar="DIR",
                     help="parent folder: mix+master every subfolder with stems")
    ap.add_argument("--out", metavar="DIR", default="out",
                    help="output folder (default: out)")
    ap.add_argument("--name", metavar="BASE",
                    help="output basename in single mode "
                         "(default: the stems folder name)")
    ap.add_argument("--map", metavar="FILE", dest="map_file",
                    help="mapping file to use (default: <stems>/keel.json)")
    ap.add_argument("--scan", action="store_true",
                    help="(re)write the keel.json mapping and exit, no render")
    ap.add_argument("--preset", metavar="NAME",
                    help="named master loudness profile "
                         f"({', '.join(sorted(recipes.PRESETS))}); "
                         "overrides the mapping's target, beaten by --lufs/--tp")
    ap.add_argument("--list-presets", action=_ListPresets,
                    help="list the named loudness presets and exit")
    ap.add_argument("--targets", metavar="LIST",
                    help="render one master PER target in a single pass (comma "
                         "list of preset names and/or LUFS numbers, e.g. "
                         "'streaming,-16,loud'); each re-runs the chain at-spec")
    ap.add_argument("--lufs", type=float, metavar="LUFS",
                    help="override the mapping's master loudness target")
    ap.add_argument("--tp", type=float, metavar="dBTP",
                    help="override the mapping's true-peak ceiling")
    ap.add_argument("--ref", metavar="FILE",
                    help="reference master; if set, Keel matches it (--lufs ignored)")
    ap.add_argument("--match-loudness", metavar="FILE", dest="match_loudness",
                    help="deterministically match a reference's LOUDNESS: measure "
                         "its integrated LUFS and use it as the target (internal "
                         "chain, no ML/spectral match). Beaten by an explicit --lufs")
    ap.add_argument("--bit-depth", type=int, choices=(16, 24, 32), default=24,
                    dest="bit_depth", metavar="N",
                    help="master word length: 16/24-bit PCM or 32-bit float "
                         "(default: 24)")
    ap.add_argument("--dither", choices=("tpdf", "shaped"), default=None,
                    help="seeded dither before sub-32-bit quantization: flat TPDF "
                         "or noise-shaped (default: none). Use when exporting 16-bit")
    ap.add_argument("--dither-seed", type=int, default=0, dest="dither_seed",
                    metavar="N",
                    help="PRNG seed for --dither (default: 0) — keeps output "
                         "deterministic")
    ap.add_argument("--format", metavar="LIST", dest="formats",
                    help="also export the master to these delivery formats "
                         "(comma list: flac,mp3,ogg,aac). WAV is always written; "
                         "FLAC is lossless, the rest lossy. AAC needs ffmpeg")
    glue_grp = ap.add_mutually_exclusive_group()
    glue_grp.add_argument("--glue", dest="glue", action="store_const", const=True,
                          default=None,
                          help="force the gentle bus-glue compressor ON "
                               "(overrides keel.json; default OFF)")
    glue_grp.add_argument("--no-glue", dest="glue", action="store_const",
                          const=False, help="force bus glue OFF")
    autotp_grp = ap.add_mutually_exclusive_group()
    autotp_grp.add_argument("--auto-tp", dest="auto_tp", action="store_const",
                            const=True, default=None,
                            help="key the true-peak ceiling to the loudness target "
                                 "(-14 LUFS->-1, -9->-2 dBTP); --tp still overrides")
    autotp_grp.add_argument("--no-auto-tp", dest="auto_tp", action="store_const",
                            const=False, help="force a fixed true-peak ceiling")
    ap.add_argument("--album", action="store_true",
                    help="album loudness-consistency mode (with --batch): one "
                         "shared gain across all tracks, preserving their relative "
                         "loudness instead of normalizing each to the same LUFS")
    ap.add_argument("--mix-only", action="store_true", help="stop after the mix")
    ap.add_argument("--master-only", action="store_true",
                    help="remaster existing out/<name>_mix.wav")
    args = ap.parse_args(argv)

    do_mix = not args.master_only
    do_master = not args.mix_only

    if args.preset:  # fail fast on a typo'd preset name
        try:
            recipes.preset_master(args.preset)
        except ValueError as e:
            ap.error(str(e))

    formats = []
    if args.formats:  # fail fast on an unknown / unavailable export format
        try:
            formats = encode.parse_formats(args.formats)
        except ValueError as e:
            ap.error(str(e))

    targets = None
    if args.targets:  # fail fast on a typo'd preset name in a target
        try:
            targets = _parse_targets(args.targets)
        except ValueError as e:
            ap.error(str(e))

    if args.match_loudness:  # deterministically match a reference's loudness
        try:
            extracted = mastering.loudness_recipe_from(args.match_loudness)
        except (ValueError, FileNotFoundError) as e:
            ap.error(str(e))
        if args.lufs is None:            # an explicit --lufs still wins
            args.lufs = extracted["target_lufs"]
            print(f"[match-loudness] {Path(args.match_loudness).name} -> "
                  f"{args.lufs} LUFS target")

    if args.album:  # album mode owns its own mix+master two-pass over a batch
        if not args.batch:
            ap.error("--album needs --batch (album consistency is across tracks)")
        if targets or args.scan or args.mix_only or args.master_only:
            ap.error("--album can't combine with --targets/--scan/--mix-only/"
                     "--master-only (it renders one shared-gain master per track)")

    if args.batch:
        if not Path(args.batch).expanduser().is_dir():
            ap.error(f"--batch folder not found: {args.batch}")
        jobs = discover_batch(args.batch)
        if not jobs:
            print(f"No subfolders with stems found under {args.batch}")
            return
    else:
        stems = Path(args.stems).expanduser().resolve()
        if not stems.is_dir():
            ap.error(f"--stems folder not found: {stems}")
        jobs = [(stems, args.name or stems.name)]

    if args.album:
        report, errors = run_album(jobs, args.out, args, formats)
    else:
        report, errors = [], 0
        for stems_dir, name in jobs:
            # A bad input for one job (malformed keel.json, unreadable/corrupt
            # audio, a samplerate mismatch) is reported as a clean line and the run
            # carries on to the next job, rather than aborting with a traceback.
            try:
                row = process_one(
                    stems_dir, args.out, name, map_file=args.map_file,
                    scan=args.scan, preset=args.preset, target_lufs=args.lufs,
                    tp_ceiling=args.tp, ref=args.ref, glue=args.glue,
                    auto_tp=args.auto_tp, bit_depth=args.bit_depth,
                    dither=args.dither, dither_seed=args.dither_seed,
                    formats=formats, targets=targets,
                    do_mix=do_mix, do_master=do_master)
            except (ValueError, FileNotFoundError) as e:
                print(f"  [error] {name}: {e}")
                errors += 1
                continue
            if row:
                report.append(row)

    if report:
        write_report(report, args.out)
    if not args.scan:
        if report:
            print(f"\nDone. Outputs in {Path(args.out).resolve()}")
        else:
            print("\nNothing rendered." +
                  (" See the [error] line(s) above." if errors else ""))
    if errors and not report:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
