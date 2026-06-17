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

STAGE / MASTER controls:
      --mix-only / --master-only          stop after mix / remaster existing mix
      --glue / --no-glue                  force the bus-glue compressor on/off
      --preset loud                       house-sound loudness profile (see below)
      --lufs -11 --tp -1                  override the mapping's master target
      --ref "C:\\refs\\master.wav"         match a reference (ignores --lufs)

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

import recipes
import mixer
import mastering

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


def process_one(stems_dir, out_dir, name, *, map_file=None, scan=False,
                preset=None, target_lufs=None, tp_ceiling=None, ref=None,
                glue=None, do_mix=True, do_master=True):
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
    master_wav = out_dir / f"{name}_master.wav"
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
        m_ov = dict(doc.get("master", {}))
        if preset:  # named profile overrides the mapping's master block
            m_ov.update(recipes.preset_master(preset))
        if target_lufs is not None:  # explicit --lufs/--tp still beat the preset
            m_ov["target_lufs"] = target_lufs
        if tp_ceiling is not None:
            m_ov["tp_ceiling_db"] = tp_ceiling
        refs_dir, ref_name = _resolve_ref(ref)
        if ref_name:
            m_ov["reference"] = ref_name
        recipe = recipes.master_recipe(m_ov)
        rep = mastering.master(mix_wav, recipe, master_wav, references_dir=refs_dir)
        row["master"] = rep
        row["target_lufs"] = recipe.get("target_lufs")
        ptag = f"  preset:{preset}" if preset else ""
        print(f"  master -> {rep['out']}  [{rep['path']}]  "
              f"{rep['lufs']} LUFS  {rep['true_peak_db']} dBTP{ptag}")

    return row if (row["mix"] or row["master"]) else None


def discover_batch(parent):
    """Immediate subfolders of `parent` that hold at least one audio file, each a
    project named after the subfolder."""
    parent = Path(parent)
    jobs = []
    for sub in sorted(p for p in parent.iterdir() if p.is_dir()):
        if mixer.autodetect(sub):
            jobs.append((sub, sub.name))
    return jobs


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
        ms = row.get("master")
        if ms:
            tgt = row.get("target_lufs")
            off = ("" if tgt is None or not isinstance(ms["lufs"], (int, float))
                   else f"  (target {tgt}, off by {round(ms['lufs'] - tgt, 2)} LU)")
            L.append(f"- Master [{ms['path']}]: **{ms['lufs']} LUFS**, "
                     f"**{ms['true_peak_db']} dBTP**{off}")
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
    ap.add_argument("--lufs", type=float, metavar="LUFS",
                    help="override the mapping's master loudness target")
    ap.add_argument("--tp", type=float, metavar="dBTP",
                    help="override the mapping's true-peak ceiling")
    ap.add_argument("--ref", metavar="FILE",
                    help="reference master; if set, Keel matches it (--lufs ignored)")
    glue_grp = ap.add_mutually_exclusive_group()
    glue_grp.add_argument("--glue", dest="glue", action="store_const", const=True,
                          default=None,
                          help="force the gentle bus-glue compressor ON "
                               "(overrides keel.json; default OFF)")
    glue_grp.add_argument("--no-glue", dest="glue", action="store_const",
                          const=False, help="force bus glue OFF")
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

    report, errors = [], 0
    for stems_dir, name in jobs:
        # A bad input for one job (malformed keel.json, unreadable/corrupt audio,
        # a samplerate mismatch) is reported as a clean line and the run carries
        # on to the next job, rather than aborting the batch with a traceback.
        try:
            row = process_one(
                stems_dir, args.out, name, map_file=args.map_file, scan=args.scan,
                preset=args.preset, target_lufs=args.lufs, tp_ceiling=args.tp,
                ref=args.ref, glue=args.glue, do_mix=do_mix, do_master=do_master)
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
