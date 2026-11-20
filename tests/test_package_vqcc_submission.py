"""Local archive-contract tests; no large competition file downloads required."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from package_vqcc_submission import package, source_entries


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.invsqrt = self.root / "best.kmb"
        self.dqi = self.root / "dqi.kmb"
        self.chem = self.root / "chem"
        self.chem.mkdir()
        self.invsqrt.write_bytes(b"test_invsqrt")
        self.dqi.write_bytes(b"test_dqi")
        for i in range(3):
            (self.chem / f"angle_k_{i}.kmb").write_bytes(f"angle_{i}".encode())
        with ZipFile(self.chem / "submission.npz", "w") as archive:
            for name in ["U", "W", "H2_I", "H1_I", "Hsym_lower", "tree_edges"]:
                archive.writestr(f"{name}.npy", b"placeholder")

    def test_exact_archive_members_and_report(self):
        output = self.root / "submissions" / "one.zip"
        report = self.root / "submissions" / "audit.json"
        receipt = package(self.invsqrt, self.dqi, self.chem, output, report)
        expected = {
            "invsqrt.kmb", "dqi.kmb", "dfthcsos/submission.npz",
            "dfthcsos/angle_k_0.kmb", "dfthcsos/angle_k_1.kmb",
            "dfthcsos/angle_k_2.kmb",
        }
        with ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()), expected)
            self.assertIsNone(archive.testzip())
        self.assertEqual(len(receipt["entries"]), len(expected))
        self.assertEqual(json.loads(report.read_text())["status"], "PACKAGED_ONLY")

    def test_refuse_overwrite(self):
        out = self.root / "one.zip"
        report = self.root / "one.json"
        package(self.invsqrt, self.dqi, self.chem, out, report)
        with self.assertRaises(FileExistsError):
            package(self.invsqrt, self.dqi, self.chem, out, report)

    def test_missing_dqi(self):
        self.dqi.unlink()
        with self.assertRaisesRegex(ValueError, "dqi"):
            source_entries(self.invsqrt, self.dqi, self.chem)

    def test_missing_angle_index(self):
        (self.chem / "angle_k_1.kmb").unlink()
        with self.assertRaisesRegex(ValueError, "consecutively"):
            source_entries(self.invsqrt, self.dqi, self.chem)

    def test_missing_array(self):
        file = self.chem / "submission.npz"
        file.unlink()
        with ZipFile(file, "w") as archive:
            archive.writestr("U.npy", b"placeholder")
        with self.assertRaisesRegex(ValueError, "missing arrays"):
            source_entries(self.invsqrt, self.dqi, self.chem)

    def test_duplicate_angle_format(self):
        (self.chem / "angle_k_1.kmx").write_text("X q0\n")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            source_entries(self.invsqrt, self.dqi, self.chem)


if __name__ == "__main__":
    unittest.main()
