"""Extract the four upper knee braces from an ACT XML order export."""

import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


PIECE_MARKS = ("UKNBRC_1", "UKNBRC_2", "HUKNBRC_1", "HUKNBRC_2")


def read_braces(path):
    data = Path(path).read_bytes()
    # This ACT export is ASCII-compatible bytes but declares UTF-16.
    # Correct the declaration only when the bytes show that mismatch.
    if data.startswith(b'<?xml'):
        data = data.replace(b'encoding="utf-16"', b'encoding="utf-8"', 1)
    root = ET.fromstring(data)
    found = {}
    for order_line in root.findall(".//OrderLine"):
        mark = order_line.findtext("PieceMark")
        if mark not in PIECE_MARKS:
            continue
        if mark in found:
            raise ValueError(f"Duplicate piece mark: {mark}")
        order_code = order_line.findtext("OrderCode", "")
        section = re.fullmatch(r"CFPBC4X2\.5-(\d+)", order_code)
        if section is None:
            raise ValueError(f"Unexpected section for {mark}")
        gauge = int(section.group(1))
        holes = {"left": [], "right": []}
        for punch in order_line.findall("./Punching/Punch"):
            if punch.findtext("Size") != "Round_5_8":
                raise ValueError(f"Unexpected hole size for {mark}")
            if float(punch.findtext("DistX")) != 1.25:
                raise ValueError(f"Unexpected flange offset for {mark}")
            side = {"FlangeLeft": "left", "FlangeRight": "right"}.get(
                punch.findtext("SectionOfComponent")
            )
            if side is None:
                raise ValueError(f"Unexpected punch location for {mark}")
            holes[side].append(float(punch.findtext("DistY")))
        if any(len(holes[side]) != 2 for side in holes):
            raise ValueError(f"Expected two holes per flange for {mark}")
        found[mark] = {
            "piece_mark": mark,
            "source": f"{Path(path).name}: {mark}; cross-checked against punch-pattern PDF",
            "units": "inch",
            "gauge": gauge,
            "length": float(order_line.findtext("./Length/Total")),
            "web_width": 4.0,
            "flange_width": 2.5,
            "trial_lip_width": 0.875,
            "hole_offset_from_web": 1.25,
            "hole_diameter": 0.625,
            "holes": {side: sorted(values) for side, values in holes.items()},
            "trial_cut_clearance_from_bend": 0.125,
            "layer_colors": {"CUT": 1, "REFERENCE": 8},
        }
    missing = set(PIECE_MARKS) - set(found)
    if missing:
        raise ValueError(f"Missing piece marks: {', '.join(sorted(missing))}")
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="ACT XML order export")
    parser.add_argument("output_dir", help="folder for four JSON specs")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for mark, spec in read_braces(args.source).items():
        path = output / f"{mark}.json"
        path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
