#!/usr/bin/env python3
"""Convert a Kickmix circuit to another Kickmix format without changing it.

Requires the official competition's kickmix Python extension on PYTHONPATH.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("target", type=Path)
    a = p.parse_args()
    if a.source.suffix not in (".kmb", ".kmx") or a.target.suffix not in (".kmb", ".kmx"):
        p.error("only .kmb and .kmx are supported")
    if a.source.resolve() == a.target.resolve() or a.target.exists():
        p.error("target must be a new path, distinct from source")
    import kickmix as km

    a.target.parent.mkdir(parents=True, exist_ok=True)
    circuit = km.Circuit.from_file(a.source, format=a.source.suffix[1:])
    circuit.to_file(a.target, format=a.target.suffix[1:])
    print(f"Converted {a.source} -> {a.target}: {len(circuit)} operations, "
          f"{circuit.num_qubits} qubits, "
          f"{circuit.operation_statistics().num_toffoli_like} static Toffoli-like gates")


if __name__ == "__main__":
    main()
