"""Resolve ACT gauge to a documented Boost material selection."""

import argparse
import json
import math
from pathlib import Path

from .__main__ import load_spec
from .import_order import PIECE_MARKS


def load_lookup(path):
    lookup = json.loads(Path(path).read_text(encoding="utf-8"))
    if not lookup.get("boost_material") or not lookup.get("material_family"):
        raise ValueError("Boost material code and family are required")
    if not isinstance(lookup.get("nominal_gauges_in"), dict):
        raise ValueError("Nominal gauge thickness lookup is required")
    raw_materials = lookup.get("available_raw_materials")
    if not isinstance(raw_materials, list) or not raw_materials:
        raise ValueError("At least one Boost raw material is required")
    seen = set()
    for row in raw_materials:
        thickness = row.get("thickness_in")
        code = row.get("code")
        if not isinstance(code, str) or not code or code in seen:
            raise ValueError("Raw material codes must be unique and nonempty")
        if not isinstance(thickness, (int, float)) or not math.isfinite(thickness) or thickness <= 0:
            raise ValueError(f"Invalid thickness for {code}")
        seen.add(code)
    return lookup


def select_material(spec, lookup):
    gauge = spec["gauge"]
    nominal = lookup["nominal_gauges_in"].get(str(gauge))
    if not isinstance(nominal, (int, float)) or not math.isfinite(nominal) or nominal <= 0:
        raise ValueError(f"No nominal {gauge} ga thickness in material lookup")
    matches = [row for row in lookup["available_raw_materials"]
               if row["thickness_in"] >= nominal]
    if not matches:
        raise ValueError(f"No Boost raw material at least {nominal} in for {gauge} ga")
    selected = min(matches, key=lambda row: (row["thickness_in"], row["code"]))
    return {
        "piece_mark": spec["piece_mark"],
        "act_gauge": gauge,
        "nominal_thickness_in": nominal,
        "boost_material": lookup["boost_material"],
        "boost_raw_material": selected["code"],
        "boost_raw_thickness_in": selected["thickness_in"],
    }


def build_manifest(sample_dir, lookup_path):
    lookup = load_lookup(lookup_path)
    assignments = []
    for mark in PIECE_MARKS:
        spec = load_spec(Path(sample_dir) / f"{mark}.json")
        if spec["piece_mark"] != mark:
            raise ValueError(f"Piece mark does not match {mark}.json")
        assignments.append(select_material(spec, lookup))
    return {
        "note": "Selection guide only; this DXF exporter does not set Boost material fields",
        "material_family": lookup["material_family"],
        "nominal_basis": lookup.get("nominal_basis"),
        "assignments": assignments,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample_dir")
    parser.add_argument("lookup")
    parser.add_argument("output")
    args = parser.parse_args()
    manifest = build_manifest(args.sample_dir, args.lookup)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
