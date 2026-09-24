import json
import tempfile
import unittest
from pathlib import Path

from brace_dxf.import_order import PIECE_MARKS
from brace_dxf.versioned import (
    LEGACY_SUFFIXES,
    archive_legacy,
    export_cut_only,
    generate_version,
    latest_version,
)


ROOT = Path(__file__).resolve().parents[1]


class VersioningTest(unittest.TestCase):
    def test_archive_preserves_each_legacy_iteration(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            for version, suffix in enumerate(LEGACY_SUFFIXES, start=1):
                for mark in PIECE_MARKS:
                    (output / f"{mark}_{suffix}.dxf").write_bytes(
                        f"{mark} version {version}".encode("ascii")
                    )
            self.assertEqual(len(archive_legacy(output)), 20)
            self.assertEqual(latest_version(output), 5)
            self.assertEqual(archive_legacy(output), [])
            for mark in PIECE_MARKS:
                self.assertEqual((output / f"{mark}_V3.dxf").read_bytes(),
                                 f"{mark} version 3".encode("ascii"))

    def test_generate_only_when_geometry_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            samples = base / "samples"
            output = base / "output"
            samples.mkdir()
            for mark in PIECE_MARKS:
                (samples / f"{mark}.json").write_bytes(
                    (ROOT / "samples" / f"{mark}.json").read_bytes()
                )
            version, files, created = generate_version(samples, output)
            self.assertEqual((version, len(files), created), (1, 4, True))
            version, files, created = generate_version(samples, output)
            self.assertEqual((version, files, created), (1, [], False))
            cut_files = export_cut_only(samples, output)
            self.assertEqual(len(cut_files), 4)
            self.assertEqual(export_cut_only(samples, output), [])
            self.assertEqual(latest_version(output), 1)
            spec_path = samples / "UKNBRC_1.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["trial_cut_clearance_from_bend"] = 0.25
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            version, files, created = generate_version(samples, output)
            self.assertEqual((version, len(files), created), (2, 4, True))
            self.assertTrue((output / "UKNBRC_1_V1.dxf").is_file())
            self.assertTrue((output / "UKNBRC_1_V2.dxf").is_file())


if __name__ == "__main__":
    unittest.main()
