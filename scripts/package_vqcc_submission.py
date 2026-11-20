#!/usr/bin/env python3
"""Assemble a VQCC Kaggle submission ZIP from local verified artifacts.

The ZIP includes the requested Invsqrt circuit and existing DQI/chemistry
baseline files, never the raw competition datasets. Source files are not
modified. Uses fresh output paths and a separate JSON provenance record.

Kaggle requires the output filename to be exactly submission.zip.\n\nIMPORTANT: Package integrity does not imply that every task passes the
competition's official full verifier. Submit and inspect Kaggle's evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


EXPECTED_NPZ = {"U", "W", "H2_I", "H1_I", "Hsym_lower", "tree_edges"}
ANGLE = re.compile(r"angle_k_(\d+)\.(kmb|kmx)\Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def source_entries(invsqrt: Path, dqi: Path, chemistry: Path) -> list[tuple[Path, str]]:
    for task, src in (("invsqrt", invsqrt), ("dqi", dqi)):
        if src.suffix not in (".kmb", ".kmx"):
            raise ValueError(f"{task}: input must be a .kmb or .kmx circuit: {src}")
        if not src.is_file() or src.is_symlink():
            raise ValueError(f"{task}: missing or unsafe circuit file: {src}")
    if not chemistry.is_dir():
        raise ValueError(f"chemistry folder does not exist: {chemistry}")
    npz = chemistry / "submission.npz"
    if not npz.is_file() or npz.is_symlink():
        raise ValueError(f"chemistry factorization missing: {npz}")

    # Check the input archive structure without reading large numerical arrays.
    with zipfile.ZipFile(npz) as source_npz:
        names = set(source_npz.namelist())
        missing = {f"{key}.npy" for key in EXPECTED_NPZ} - names
        if missing:
            raise ValueError(f"chemistry NPZ missing arrays: {sorted(missing)}")

    circuits: dict[int, Path] = {}
    for file in chemistry.iterdir():
        if not file.is_file() or file.is_symlink():
            continue
        m = ANGLE.fullmatch(file.name)
        if not m:
            continue
        number = int(m.group(1))
        if number in circuits:
            raise ValueError(f"ambiguous chemistry angle index {number}: duplicate formats")
        circuits[number] = file

    if not circuits:
        raise ValueError(f"no chemistry angle_k_*.kmb/.kmx circuits in {chemistry}")
    if sorted(circuits) != list(range(len(circuits))):
        raise ValueError(f"chemistry circuits not consecutively numbered from zero: {sorted(circuits)}")

    items = [
        (invsqrt, "invsqrt" + invsqrt.suffix),
        (dqi, "dqi" + dqi.suffix),
        (npz, "dfthcsos/submission.npz"),
    ]
    items.extend((circuits[i], f"dfthcsos/angle_k_{i}{circuits[i].suffix}")
                 for i in range(len(circuits)))
    return items


def package(invsqrt: Path, dqi: Path, chemistry: Path, output: Path, report: Path) -> dict:
    # Competition-specific upload rule, corrected from a user-observed rejection.
    if output.name != "submission.zip":
        raise ValueError(
            f"Kaggle expects the archive to be named exactly submission.zip, got {output.name!r}"
        )
    if output.resolve() == report.resolve():
        raise ValueError("ZIP output and audit report paths must differ")
    if output.exists() or report.exists():
        raise FileExistsError("refusing to overwrite existing ZIP or audit report")

    sources = source_entries(invsqrt, dqi, chemistry)
    for src, _ in sources:
        if src.resolve() in {output.resolve(), report.resolve()}:
            raise ValueError("refusing to use an output as an input")

    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    try:
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            for source, destination in sources:
                archive.write(source, arcname=destination)
                entries.append({
                    "path_in_zip": destination,
                    "source": str(source),
                    "uncompressed_bytes": source.stat().st_size,
                    "sha256": sha256_file(source),
                })

        with zipfile.ZipFile(output, "r") as archive:
            actual = set(archive.namelist())
            expected = {dest for _, dest in sources}
            if actual != expected:
                raise ValueError(f"ZIP contents mismatch: actual={actual}, expected={expected}")
            corrupt = archive.testzip()
            if corrupt is not None:
                raise ValueError(f"ZIP CRC test failed at {corrupt}")

        receipt = {
            "competition": "google-verifiable-quantum-circuit-compilation",
            "status": "PACKAGED_ONLY",
            "official_full_task_verification": "NOT_ESTABLISHED",
            "zip_path": str(output),
            "zip_size_bytes": output.stat().st_size,
            "zip_sha256": sha256_file(output),
            "entries": entries,
            "warning": "ZIP is structurally valid; Kaggle must score all 3 tasks.",
        }
        report.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return receipt
    except Exception:
        output.unlink(missing_ok=True)
        raise


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--invsqrt", type=Path, required=True,
                   help="Exact winning Invsqrt .kmb from Experiment 003")
    p.add_argument("--dqi", type=Path, default=Path("sample_submission/dqi.kmb"),
                   help="Existing large DQI circuit (default: sample_submission/dqi.kmb)")
    p.add_argument("--chemistry", type=Path,
                   default=Path("sample_submission/dfthcsos"),
                   help="Directory containing angle_k_* circuits and submission.npz")
    p.add_argument("--output", type=Path, required=True,
                   help="New ZIP; final filename must be exactly submission.zip")
    p.add_argument("--report", type=Path, required=True,
                   help="New JSON receipt alongside ZIP (NOT included inside ZIP)")
    args = p.parse_args()
    if args.output.name != "submission.zip":
        p.error("Kaggle requires the filename submission.zip exactly")
    try:
        receipt = package(args.invsqrt, args.dqi, args.chemistry,
                          args.output, args.report)
    except (ValueError, FileNotFoundError, PermissionError,
            OSError, zipfile.BadZipFile) as ex:
        p.exit(1, f"PACKAGING FAILED: {ex}\n")
    print(json.dumps({
        "status": receipt["status"],
        "zip_path": receipt["zip_path"],
        "zip_size_bytes": receipt["zip_size_bytes"],
        "zip_sha256": receipt["zip_sha256"],
        "entry_paths": [e["path_in_zip"] for e in receipt["entries"]],
        "audit_path": str(args.report),
        "official_verification": receipt["official_full_task_verification"],
    }, indent=2))


if __name__ == "__main__":
    main()
