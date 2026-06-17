# Keel — automix + automaster engine.
# Copyright (C) 2026 Felipe Carvajal Brown
#
# Licensed under the GNU Affero General Public License v3.0 (see LICENSE).
# A commercial license is available — see COMMERCIAL-LICENSE.md
# or contact fcarvajalbrown@gmail.com.
"""
test_engine.py  —  Keel's safety net (stdlib unittest, no extra dependency).

Synthesizes tiny stems on the fly (no committed audio) and asserts the
properties Keel is supposed to guarantee:

  * DETERMINISM — same stems + same recipe -> byte-identical output, every run.
  * LANDING     — the master hits the exact target LUFS and stays under the
                  true-peak ceiling, including via a named preset.
  * GROUP BALANCE — a doubled label is balanced as ONE group (two copies don't
                    come out louder than one).
  * REGRESSIONS — a label mixing mono + stereo files does not crash (the bug
                  fixed in Phase 2), and >2-channel files coerce to stereo.
  * LABELING    — token/word-boundary matching ("OH"->drums, "john"->other).
  * RECIPES     — preset values + deep-merge of overrides onto the defaults.

Run from the repo root:
    .venv\\Scripts\\python.exe -m unittest discover -s tests
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

import keel
import recipes
import mixer
import mastering
import meters
import build

RATE = 44100
SECONDS = 3.0  # > the LUFS gating window, short enough to stay fast


def _sine(path, freq=220.0, amp=0.2, seconds=SECONDS, rate=RATE, stereo=False):
    """Write a deterministic sine-wave stem (no randomness) to `path`."""
    t = np.arange(int(seconds * rate)) / rate
    sig = (amp * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)
    data = np.column_stack([sig, sig]) if stereo else sig.reshape(-1, 1)
    sf.write(str(path), data, rate, subtype="PCM_24")


def _make_song(folder):
    """A minimal but realistic stem set: vocals, two guitars, bass, drums."""
    folder = Path(folder)
    _sine(folder / "lead_vox.wav", freq=330.0)
    _sine(folder / "gtr_1.wav", freq=440.0)
    _sine(folder / "gtr_2.wav", freq=445.0)
    _sine(folder / "bass_DI.wav", freq=110.0)
    _sine(folder / "kick.wav", freq=60.0)
    return folder


def _group_lufs(result):
    """Sum the per-file buffers of one processed group and measure its LUFS."""
    bufs, rate, _info = result
    n = max(b.shape[0] for b in bufs)
    summed = np.zeros((n, 2), dtype=np.float64)
    for b in bufs:
        summed[: b.shape[0]] += b
    return meters.integrated_lufs(summed, rate)


class TestRecipes(unittest.TestCase):
    def test_preset_values(self):
        self.assertEqual(keel.preset_master("streaming"),
                         {"target_lufs": -14.0, "tp_ceiling_db": -1.0})
        self.assertEqual(keel.preset_master("loud")["target_lufs"], -10.0)
        self.assertEqual(keel.preset_master("broadcast")["target_lufs"], -16.0)
        for p in keel.PRESETS.values():  # every preset stays at the safe ceiling
            self.assertEqual(p["tp_ceiling_db"], -1.0)

    def test_preset_returns_copy(self):
        a = keel.preset_master("loud")
        a["target_lufs"] = 0.0
        self.assertEqual(keel.PRESETS["loud"]["target_lufs"], -10.0)

    def test_unknown_preset_raises(self):
        with self.assertRaises(ValueError):
            keel.preset_master("nope")

    def test_default_preset_matches_master_default(self):
        self.assertEqual(keel.preset_master(keel.DEFAULT_PRESET)["target_lufs"],
                         recipes.DEFAULT_MASTER["target_lufs"])

    def test_mix_recipe_deep_merge(self):
        r = recipes.mix_recipe({"balance": {"synth": -4.5}})
        self.assertEqual(r["balance"]["synth"], -4.5)        # override wins
        self.assertEqual(r["balance"]["vocals"], 0.0)        # default kept
        self.assertEqual(r["balance"]["drums"],
                         recipes.DEFAULT_BALANCE["drums"])

    def test_master_recipe_deep_merge(self):
        r = recipes.master_recipe({"target_lufs": -11.0})
        self.assertEqual(r["target_lufs"], -11.0)
        self.assertEqual(r["tp_ceiling_db"],
                         recipes.DEFAULT_MASTER["tp_ceiling_db"])


class TestUserPresets(unittest.TestCase):
    def setUp(self):
        import userpresets
        self.up = userpresets
        # isolate the store to a temp file so the real one is never touched
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = self.up.STORE
        self.up.STORE = Path(self._tmp.name) / "userpresets.json"

    def tearDown(self):
        self.up.STORE = self._orig
        self._tmp.cleanup()

    def test_save_load_delete_roundtrip(self):
        self.up.save_user_preset("mine", {"target_lufs": -12.0,
                                          "tp_ceiling_db": -1.0})
        self.assertEqual(self.up.load_user_presets()["mine"]["target_lufs"], -12.0)
        # built-ins overlaid with the user preset
        merged = self.up.all_presets()
        self.assertIn("streaming", merged)
        self.assertIn("mine", merged)
        self.up.delete_user_preset("mine")
        self.assertNotIn("mine", self.up.load_user_presets())

    def test_cannot_shadow_builtin(self):
        with self.assertRaises(ValueError):
            self.up.save_user_preset("streaming", {"target_lufs": -1.0,
                                                   "tp_ceiling_db": -1.0})

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            self.up.save_user_preset("  ", {"target_lufs": -14.0,
                                            "tp_ceiling_db": -1.0})


class TestLabeling(unittest.TestCase):
    def test_tokenize(self):
        self.assertEqual(mixer._tokenize("Guitar 1"), ["guitar"])
        self.assertEqual(mixer._tokenize("BassAmp1"), ["bass", "amp"])
        self.assertEqual(mixer._tokenize("01_Kick"), ["kick"])

    def test_match_boundaries(self):
        # short aliases are anchored at a token start: they hit the real thing...
        self.assertEqual(mixer._match_label("OH_L"), "drums")     # overhead mic
        self.assertEqual(mixer._match_label("Ride"), "drums")
        self.assertEqual(mixer._match_label("lead_vox"), "vocals")
        # ...but never a substring lookalike
        self.assertEqual(mixer._match_label("john"), mixer.OTHER_LABEL)
        self.assertEqual(mixer._match_label("pride"), mixer.OTHER_LABEL)

    def test_autodetect_groups_kit(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("Kick.wav", "Snare.wav", "OH_L.wav", "OH_R.wav"):
                _sine(Path(d) / n)
            fmap = mixer.autodetect(d)
            self.assertTrue(all(v == "drums" for v in fmap.values()))


class TestToStereo(unittest.TestCase):
    def test_mono_to_stereo(self):
        out = mixer._to_stereo(np.ones((100, 1), dtype=np.float32))
        self.assertEqual(out.shape, (100, 2))

    def test_stereo_passthrough(self):
        a = np.ones((100, 2), dtype=np.float32)
        self.assertEqual(mixer._to_stereo(a).shape, (100, 2))

    def test_multichannel_coerced(self):
        a = np.ones((100, 6), dtype=np.float32)
        self.assertEqual(mixer._to_stereo(a).shape, (100, 2))


class TestMixDeterminism(unittest.TestCase):
    def test_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            folder = _make_song(d)
            recipe = recipes.mix_recipe()
            mapping = mixer.autodetect(folder)
            out1, out2 = Path(d) / "m1.wav", Path(d) / "m2.wav"
            mixer.mix(folder, recipe, out1, mapping=mapping)
            mixer.mix(folder, recipe, out2, mapping=mapping)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())


class TestGroupBalance(unittest.TestCase):
    def test_double_not_louder_than_single(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "gtr.wav"
            _sine(p, freq=440.0)
            recipe = recipes.mix_recipe()
            single = mixer._process_group("guitar", [p], recipe)
            double = mixer._process_group("guitar", [p, p], recipe)
            self.assertAlmostEqual(_group_lufs(single), _group_lufs(double),
                                   delta=0.5)
            # and the group lands on its intended internal target
            target = mixer.INTERNAL_ANCHOR_LUFS + recipe["balance"]["guitar"]
            self.assertAlmostEqual(_group_lufs(single), target, delta=0.6)

    def test_mixed_mono_and_stereo_group(self):
        # regression: a label holding a mono close mic + a stereo overhead used
        # to crash the loudness measurement. It must just work now.
        with tempfile.TemporaryDirectory() as d:
            mono = Path(d) / "kick.wav"
            stereo = Path(d) / "OH.wav"
            _sine(mono, freq=60.0, stereo=False)
            _sine(stereo, freq=8000.0, stereo=True)
            recipe = recipes.mix_recipe()
            bufs, rate, info = mixer._process_group("drums", [mono, stereo],
                                                    recipe)
            self.assertEqual(info["files"], 2)
            self.assertTrue(np.isfinite(_group_lufs((bufs, rate, info))))


class TestMasterLanding(unittest.TestCase):
    def _mix(self, d):
        folder = _make_song(d)
        mix_wav = Path(d) / "mix.wav"
        mixer.mix(folder, recipes.mix_recipe(), mix_wav,
                  mapping=mixer.autodetect(folder))
        return mix_wav

    def test_internal_hits_target_and_ceiling(self):
        with tempfile.TemporaryDirectory() as d:
            mix_wav = self._mix(d)
            master_wav = Path(d) / "master.wav"
            recipe = recipes.master_recipe({"target_lufs": -14.0,
                                            "tp_ceiling_db": -1.0})
            rep = mastering.master(mix_wav, recipe, master_wav)
            self.assertAlmostEqual(rep["lufs"], -14.0, delta=0.3)
            self.assertLessEqual(rep["true_peak_db"], -1.0 + 0.2)
            self.assertEqual(rep["path"], "internal")

    def test_master_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            mix_wav = self._mix(d)
            recipe = recipes.master_recipe()
            a, b = Path(d) / "a.wav", Path(d) / "b.wav"
            mastering.master(mix_wav, recipe, a)
            mastering.master(mix_wav, recipe, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())


class TestBuildIntegration(unittest.TestCase):
    def test_process_one_with_preset(self):
        with tempfile.TemporaryDirectory() as d, \
                tempfile.TemporaryDirectory() as out:
            folder = _make_song(d)
            row = build.process_one(folder, out, "song", preset="loud")
            self.assertTrue((Path(out) / "song_mix.wav").exists())
            self.assertTrue((Path(out) / "song_master.wav").exists())
            self.assertAlmostEqual(row["master"]["lufs"], -10.0, delta=0.3)
            # the loud preset overrode the keel.json default target
            self.assertEqual(row["target_lufs"], -10.0)

    def test_glue_toggle_plumbing(self):
        # The --glue/keel.json toggle must thread through to a valid render on
        # both paths (glue only audibly engages on a hot bus, an ear call left
        # to the user; here we assert the plumbing renders cleanly either way).
        with tempfile.TemporaryDirectory() as d, \
                tempfile.TemporaryDirectory() as out:
            folder = _make_song(d)
            off = build.process_one(folder, out, "off", do_master=False)
            on = build.process_one(folder, out, "on", do_master=False, glue=True)
            for tag in ("off", "on"):
                wav = Path(out) / f"{tag}_mix.wav"
                self.assertTrue(wav.exists())
                a, _ = sf.read(str(wav), always_2d=True)
                self.assertTrue(np.all(np.isfinite(a)))
            self.assertIsNotNone(off["mix"])
            self.assertIsNotNone(on["mix"])


class TestEdgeCases(unittest.TestCase):
    """Bad / degenerate input must degrade gracefully, never crash with a raw
    traceback or leak a `nan` into the output or the report."""

    # --- silent audio: handled, not an error ---
    def test_silent_stem_renders_finite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "silent.wav"
            sf.write(str(p), np.zeros((int(SECONDS * RATE), 1), np.float32),
                     RATE, subtype="PCM_24")
            bufs, _rate, info = mixer._process_group("vocals", [p],
                                                     recipes.mix_recipe())
            self.assertIsNone(info["pre_lufs"])     # below the gate -> None
            self.assertEqual(info["gain_db"], 0.0)  # no gain guessed on silence
            self.assertTrue(all(np.all(np.isfinite(b)) for b in bufs))

    def test_silent_master_no_crash(self):
        with tempfile.TemporaryDirectory() as d:
            mix = Path(d) / "mix.wav"
            sf.write(str(mix), np.zeros((int(SECONDS * RATE), 2), np.float32),
                     RATE, subtype="PCM_24")
            rep = mastering.master(mix, recipes.master_recipe(),
                                   Path(d) / "master.wav")
            self.assertFalse(np.isfinite(rep["lufs"]))     # -inf, not a crash
            self.assertTrue((Path(d) / "master.wav").exists())

    # --- NaN/Inf audio: sanitized to silence at load ---
    def test_nan_inf_sanitized_at_load(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "nan.wav"
            data = np.full((int(SECONDS * RATE), 1), 0.2, np.float32)
            data[1000] = np.nan
            data[2000] = np.inf
            data[3000] = -np.inf
            # a FLOAT-subtype WAV preserves non-finite samples on disk (PCM would
            # clamp them), so this is the real "corrupt take" case.
            sf.write(str(p), data, RATE, subtype="FLOAT")
            back, _ = sf.read(str(p), dtype="float32", always_2d=True)
            self.assertTrue(not np.all(np.isfinite(back)))   # really on disk
            audio, _ = mixer._load(p)
            self.assertTrue(np.all(np.isfinite(audio)))      # guard cleaned it

    def test_nan_stem_yields_finite_mix_report(self):
        # regression for the leak the probe found: a single NaN sample used to
        # propagate into the mix bus and surface as peak_dbfs == nan in the
        # report. Both the rendered bus and the report must stay finite now.
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "nan.wav"
            data = np.full((int(SECONDS * RATE), 1), 0.2, np.float32)
            data[1000] = np.nan
            sf.write(str(p), data, RATE, subtype="FLOAT")
            rep = mixer.mix(d, recipes.mix_recipe(), Path(d) / "mix.wav",
                            mapping={"nan.wav": "vocals"})
            self.assertTrue(np.isfinite(rep["peak_dbfs"]))
            a, _ = sf.read(str(Path(d) / "mix.wav"), dtype="float32",
                           always_2d=True)
            self.assertTrue(np.all(np.isfinite(a)))

    # --- corrupt / unreadable audio: clear error, no raw LibsndfileError ---
    def test_corrupt_audio_clear_error(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corrupt.wav"
            p.write_text("this is not audio", encoding="utf-8")
            with self.assertRaises(ValueError) as cm:
                mixer._load(p)
            self.assertIn("not a readable audio file", str(cm.exception))

    # --- samplerate mismatch within a group: clear error ---
    def test_samplerate_mismatch_in_group(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.wav", Path(d) / "b.wav"
            _sine(a, rate=44100)
            t = np.arange(int(SECONDS * 48000)) / 48000
            sf.write(str(b), (0.2 * np.sin(2 * np.pi * 220 * t)
                              ).astype(np.float32).reshape(-1, 1),
                     48000, subtype="PCM_24")
            with self.assertRaises(ValueError) as cm:
                mixer._process_group("vocals", [a, b], recipes.mix_recipe())
            self.assertIn("samplerate", str(cm.exception))

    # --- malformed keel.json: clear error, file left untouched ---
    def test_malformed_keeljson_clear_error_and_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "keel.json"
            broken = '{ "stems": { not valid '
            mpath.write_text(broken, encoding="utf-8")
            with self.assertRaises(ValueError) as cm:
                build.load_mapping_doc(mpath)
            self.assertIn("not valid JSON", str(cm.exception))
            self.assertEqual(mpath.read_text(encoding="utf-8"), broken)

    def test_process_one_malformed_keeljson_not_overwritten(self):
        # a hand-edit typo must NOT be silently overwritten by auto-detect.
        with tempfile.TemporaryDirectory() as d, \
                tempfile.TemporaryDirectory() as out:
            folder = _make_song(d)
            mpath = Path(d) / "keel.json"
            broken = '{ oops '
            mpath.write_text(broken, encoding="utf-8")
            with self.assertRaises(ValueError):
                build.process_one(folder, out, "song")
            self.assertEqual(mpath.read_text(encoding="utf-8"), broken)

    # --- keel.json is NOT required: a missing one is auto-detected ---
    def test_missing_keeljson_autoregenerated(self):
        with tempfile.TemporaryDirectory() as d, \
                tempfile.TemporaryDirectory() as out:
            folder = _make_song(d)
            self.assertFalse((Path(d) / "keel.json").exists())
            row = build.process_one(folder, out, "song", do_master=False)
            self.assertTrue((Path(d) / "keel.json").exists())   # seeded by detect
            self.assertTrue((Path(out) / "song_mix.wav").exists())
            self.assertIsNotNone(row["mix"])


class TestBatchIntegration(unittest.TestCase):
    """End-to-end --batch coverage: discovery, a full two-song render, and
    resilience when one job has bad input."""

    def _album(self, parent):
        for name in ("songA", "songB"):
            sub = Path(parent) / name
            sub.mkdir()
            _make_song(sub)
        # a subfolder with no stems must be ignored by discovery
        notes = Path(parent) / "notes"
        notes.mkdir()
        (notes / "readme.txt").write_text("x", encoding="utf-8")

    def test_discover_batch_only_stem_folders(self):
        with tempfile.TemporaryDirectory() as d:
            self._album(d)
            names = sorted(n for _, n in build.discover_batch(d))
            self.assertEqual(names, ["songA", "songB"])   # 'notes' excluded

    def test_batch_end_to_end_via_main(self):
        with tempfile.TemporaryDirectory() as d, \
                tempfile.TemporaryDirectory() as out:
            self._album(d)
            build.main(["--batch", d, "--out", out, "--preset", "streaming"])
            for name in ("songA", "songB"):
                self.assertTrue((Path(out) / f"{name}_mix.wav").exists())
                self.assertTrue((Path(out) / f"{name}_master.wav").exists())
            report = (Path(out) / "REPORT.md")
            self.assertTrue(report.exists())
            txt = report.read_text(encoding="utf-8")
            self.assertIn("songA", txt)
            self.assertIn("songB", txt)

    def test_batch_continues_past_a_bad_job(self):
        # good folder + a folder with a malformed keel.json: the good one still
        # renders, the bad one is reported but does not abort the batch.
        with tempfile.TemporaryDirectory() as d, \
                tempfile.TemporaryDirectory() as out:
            good = Path(d) / "good"
            good.mkdir()
            _make_song(good)
            bad = Path(d) / "bad"
            bad.mkdir()
            _make_song(bad)
            (bad / "keel.json").write_text("{ broken", encoding="utf-8")
            build.main(["--batch", d, "--out", out, "--mix-only"])
            self.assertTrue((Path(out) / "good_mix.wav").exists())
            self.assertFalse((Path(out) / "bad_mix.wav").exists())


if __name__ == "__main__":
    unittest.main()
