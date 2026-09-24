"""Archive past trials as V1–V5 and number future brace sets consecutively."""

import argparse
import re
from pathlib import Path

from .__main__ import build_dxf, inspect_dxf, load_spec
from .import_order import PIECE_MARKS


LEGACY_SUFFIXES = (
    "trial",
    "sketch_trial",
    "rect_trial",
    "tangent_trial",
    "bend_span_trial",
)


def archive_legacy(output_dir):
    output = Path(output_dir)
    archived = []
    for version, suffix in enumerate(LEGACY_SUFFIXES, start=1):
        for mark in PIECE_MARKS:
            source = output / f"{mark}_{suffix}.dxf"
            destination = output / f"{mark}_V{version}.dxf"
            data = source.read_bytes()
            if destination.exists():
                if destination.read_bytes() != data:
                    raise ValueError(f"Versioned file differs from legacy source: {destination}")
                continue
            with destination.open("xb") as stream:
                stream.write(data)
            archived.append(destination)
    return archived


def latest_version(output_dir):
    output = Path(output_dir)
    pattern = re.compile(r"(?:UKNBRC_[12]|HUKNBRC_[12])_V([1-9][0-9]*)\.dxf$")
    versions = [int(match.group(1)) for path in output.glob("*_V*.dxf")
                if (match := pattern.fullmatch(path.name))]
    latest = max(versions, default=0)
    if latest and any(not (output / f"{mark}_V{latest}.dxf").is_file()
                      for mark in PIECE_MARKS):
        raise ValueError(f"V{latest} is incomplete; resolve it before generating another set")
    return latest


def generate_version(sample_dir, output_dir):
    samples = Path(sample_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    data = {}
    for mark in PIECE_MARKS:
        spec = load_spec(samples / f"{mark}.json")
        if spec["piece_mark"] != mark:
            raise ValueError(f"Piece mark does not match {mark}.json")
        data[mark] = build_dxf(spec).encode("ascii")
    latest = latest_version(output)
    if latest and all((output / f"{mark}_V{latest}.dxf").read_bytes() == data[mark]
                      for mark in PIECE_MARKS):
        return latest, [], False
    version = latest + 1
    targets = [output / f"{mark}_V{version}.dxf" for mark in PIECE_MARKS]
    if any(path.exists() for path in targets):
        raise FileExistsError(f"V{version} already exists")
    for mark, path in zip(PIECE_MARKS, targets):
        with path.open("xb") as stream:
            stream.write(data[mark])
    return version, targets, True


def export_cut_only(sample_dir, output_dir):
    """Write companions of the current version with only its closed cut path."""
    samples = Path(sample_dir)
    output = Path(output_dir)
    version = latest_version(output)
    if not version:
        raise ValueError("Generate a numbered DXF set before exporting cut-only files")
    exported = []
    for mark in PIECE_MARKS:
        spec = load_spec(samples / f"{mark}.json")
        if spec["piece_mark"] != mark:
            raise ValueError(f"Piece mark does not match {mark}.json")
        full = output / f"{mark}_V{version}.dxf"
        if full.read_bytes() != build_dxf(spec).encode("ascii"):
            raise ValueError(f"Current reference DXF differs from sample: {full}")
        destination = output / f"{mark}_V{version}_CUT_ONLY.dxf"
        data = build_dxf(spec, include_reference=False).encode("ascii")
        if destination.exists():
            if destination.read_bytes() != data:
                raise ValueError(f"Existing cut-only file differs: {destination}")
            continue
        with destination.open("xb") as stream:
            stream.write(data)
        inspect_dxf(destination, cut_only=True)
        exported.append(destination)
    return exported


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    archive = subparsers.add_parser("archive", help="copy old trial names to V1–V5")
    archive.add_argument("output_dir")
    generate = subparsers.add_parser("generate", help="write next version if geometry changed")
    generate.add_argument("sample_dir")
    generate.add_argument("output_dir")
    cut_only = subparsers.add_parser("cut-only", help="export current version's cut path alone")
    cut_only.add_argument("sample_dir")
    cut_only.add_argument("output_dir")
    args = parser.parse_args()
    if args.command == "archive":
        paths = archive_legacy(args.output_dir)
        print(f"Archived {len(paths)} files; latest is V{latest_version(args.output_dir)}")
    elif args.command == "generate":
        version, paths, created = generate_version(args.sample_dir, args.output_dir)
        if created:
            print(f"Created V{version}: {', '.join(str(path) for path in paths)}")
        else:
            print(f"No DXF change; V{version} is current")
    else:
        paths = export_cut_only(args.sample_dir, args.output_dir)
        print(f"Created {len(paths)} cut-only companions for V{latest_version(args.output_dir)}")


if __name__ == "__main__":
    main()
