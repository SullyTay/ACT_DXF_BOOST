"""Generate and inspect a deliberately simple trial flat-pattern DXF."""

import argparse
import json
import math
from pathlib import Path


def fmt(value):
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".") or "0"
    return str(value)


def pairs(*items):
    return "".join(f"{code}\n{fmt(value)}\n" for code, value in items)


def load_spec(path):
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    if spec.get("units") != "inch":
        raise ValueError("Only inch units are supported")
    for key in ("length", "web_width", "flange_width", "trial_lip_width",
                "hole_offset_from_web", "hole_diameter",
                "trial_cut_clearance_from_bend"):
        value = spec.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{key} must be a positive finite number")
    length = spec["length"]
    diameter = spec["hole_diameter"]
    radius = diameter / 2
    offset = spec["hole_offset_from_web"]
    if not diameter / 2 < offset < spec["flange_width"] - diameter / 2:
        raise ValueError("Holes do not fit across the flange")
    if spec["trial_cut_clearance_from_bend"] >= spec["flange_width"]:
        raise ValueError("Lengthwise cut must stay within the flange")
    for side in ("left", "right"):
        holes = spec.get("holes", {}).get(side)
        if not isinstance(holes, list) or len(holes) != 2 or any(
            not isinstance(x, (int, float)) or not math.isfinite(x) for x in holes
        ):
            raise ValueError(f"{side} needs two finite hole positions")
        near, far = holes
        if not (diameter / 2 < near < far < length - diameter / 2):
            raise ValueError(f"{side} holes do not fit in member length")
        if near + radius >= far - radius:
            raise ValueError(f"{side} tangent cuts would overlap")
    for name in ("CUT", "REFERENCE"):
        color = spec.get("layer_colors", {}).get(name)
        if not isinstance(color, int) or not 1 <= color <= 255:
            raise ValueError(f"{name} needs an ACI layer color from 1 to 255")
    return spec


def outline(spec):
    """Nominal rectangular source blank retained as reference geometry."""
    length = spec["length"]
    flange = spec["flange_width"]
    web = spec["web_width"]
    lip = spec["trial_lip_width"]
    full_width = 2 * lip + 2 * flange + web
    return [(0, 0), (length, 0), (length, full_width), (0, full_width)]


def lwpolyline(points, layer="CUT", closed=True):
    result = pairs((0, "LWPOLYLINE"), (100, "AcDbEntity"), (8, layer),
                   (100, "AcDbPolyline"), (90, len(points)), (70, int(closed)))
    for x, y in points:
        result += pairs((10, x), (20, y))
    return result


def circle(x, y, radius):
    return pairs((0, "CIRCLE"), (100, "AcDbEntity"), (8, "REFERENCE"),
                 (100, "AcDbCircle"), (10, x), (20, y), (30, 0), (40, radius))


def line(x0, y0, x1, y1, layer, color=None, linetype=None):
    tags = [(0, "LINE"), (100, "AcDbEntity"), (8, layer)]
    if color is not None:
        tags.append((62, color))
    if linetype is not None:
        tags.append((6, linetype))
    tags.extend(((100, "AcDbLine"), (10, x0), (20, y0), (30, 0),
                 (11, x1), (21, y1), (31, 0)))
    return pairs(*tags)


def inner_cut_paths(spec):
    lip = spec["trial_lip_width"]
    web_bottom = lip + spec["flange_width"]
    web_top = web_bottom + spec["web_width"]
    full_width = web_top + spec["flange_width"] + lip
    radius = spec["hole_diameter"] / 2
    clearance = spec["trial_cut_clearance_from_bend"]
    length = spec["length"]
    paths = []
    for side, y_root, y_cut, y_outer in (
        ("right", web_bottom, web_bottom - clearance, 0),
        ("left", web_top, web_top + clearance, full_width),
    ):
        near, far = spec["holes"][side]
        paths.append([(0, y_root), (0, y_cut), (near + radius, y_cut),
                      (near + radius, y_outer)])
        paths.append([(length, y_root), (length, y_cut), (far - radius, y_cut),
                      (far - radius, y_outer)])
    return paths


def bend_spans(cut_paths):
    """Keep each bend only between its two flange cut stations."""
    return [
        (cut_paths[0][2][0], cut_paths[0][0][1], cut_paths[1][2][0]),
        (cut_paths[2][2][0], cut_paths[2][0][1], cut_paths[3][2][0]),
    ]


def finished_outline(spec):
    """One closed cut path, including web ends and both long exterior edges."""
    paths = inner_cut_paths(spec)
    right_near = paths[0][2][0]
    right_far = paths[1][2][0]
    left_near = paths[2][2][0]
    left_far = paths[3][2][0]
    bottom_cut_y = paths[0][2][1]
    top_cut_y = paths[2][2][1]
    length = spec["length"]
    width = outline(spec)[2][1]
    return [
        (right_near, 0), (right_far, 0),
        (right_far, bottom_cut_y), (length, bottom_cut_y),
        (length, top_cut_y), (left_far, top_cut_y),
        (left_far, width), (left_near, width),
        (left_near, top_cut_y), (0, top_cut_y),
        (0, bottom_cut_y), (right_near, bottom_cut_y),
    ]


def build_dxf(spec):
    flange = spec["flange_width"]
    web = spec["web_width"]
    lip = spec["trial_lip_width"]
    offset = spec["hole_offset_from_web"]
    entities = lwpolyline(finished_outline(spec), "CUT")
    entities += lwpolyline(outline(spec), "REFERENCE")
    web_bottom = lip + flange
    web_top = web_bottom + web
    cut_paths = inner_cut_paths(spec)
    for side, y, low, high in (
        ("right", lip + flange - offset, lip, web_bottom),
        ("left", web_top + offset, web_top, web_top + flange),
    ):
        for x in spec["holes"][side]:
            entities += circle(x, y, spec["hole_diameter"] / 2)
            entities += line(x, low, x, high, "REFERENCE")
    for x_start, y, x_end in bend_spans(cut_paths):
        entities += line(x_start, y, x_end, y, "REFERENCE", color=2,
                         linetype="DASHED")
    linetypes = (
        pairs((0, "LTYPE"), (2, "CONTINUOUS"), (70, 0),
              (3, "Solid line"), (72, 65), (73, 0), (40, 0))
        + pairs((0, "LTYPE"), (2, "DASHED"), (70, 0),
                (3, "Dashed line"), (72, 65), (73, 2), (40, 0.375),
                (49, 0.25), (74, 0), (49, -0.125), (74, 0))
    )
    layers = ""
    for name in ("CUT", "REFERENCE"):
        layers += pairs((0, "LAYER"), (2, name), (70, 0),
                        (62, spec["layer_colors"][name]),
                        (6, "CONTINUOUS"))
    return (
        pairs((0, "SECTION"), (2, "HEADER"), (9, "$ACADVER"), (1, "AC1015"),
              (9, "$INSUNITS"), (70, 1), (0, "ENDSEC"))
        + pairs((0, "SECTION"), (2, "TABLES"), (0, "TABLE"),
                (2, "LTYPE"), (70, 2))
        + linetypes
        + pairs((0, "ENDTAB"), (0, "TABLE"), (2, "LAYER"), (70, 2))
        + layers
        + pairs((0, "ENDTAB"), (0, "ENDSEC"), (0, "SECTION"),
                (2, "ENTITIES"))
        + entities
        + pairs((0, "ENDSEC"), (0, "EOF"))
    )


def inspect_dxf(path):
    lines = Path(path).read_text(encoding="ascii").splitlines()
    if len(lines) % 2:
        raise ValueError("DXF has an unmatched group code")
    data = list(zip(lines[0::2], lines[1::2]))
    counts = {"LWPOLYLINE": 0, "CIRCLE": 0, "LINE": 0}
    layers = {name: set() for name in ("CUT", "REFERENCE")}
    in_entities = False
    entity = None
    for code, value in data:
        if (code, value) == ("2", "ENTITIES"):
            in_entities = True
        elif in_entities and (code, value) == ("0", "ENDSEC"):
            in_entities = False
        elif in_entities and code == "0":
            entity = value
            if entity not in counts:
                raise ValueError(f"Unexpected entity: {entity}")
            counts[entity] += 1
        elif in_entities and code == "8":
            if value not in layers:
                raise ValueError(f"Unexpected layer: {value}")
            layers[value].add(entity)
    expected = {"LWPOLYLINE": 2, "CIRCLE": 4, "LINE": 6}
    expected_layers = {"CUT": {"LWPOLYLINE"},
                       "REFERENCE": {"LWPOLYLINE", "CIRCLE", "LINE"}}
    if counts != expected or layers != expected_layers:
        raise ValueError(f"Unexpected DXF content: {counts}, {layers}")
    if ("9", "$INSUNITS") not in data or ("70", "1") not in data:
        raise ValueError("DXF inch units are missing")
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="JSON spec, or 'validate'")
    parser.add_argument("output", help="output DXF, or DXF to validate")
    args = parser.parse_args()
    if args.source == "validate":
        print(inspect_dxf(args.output))
        return
    spec = load_spec(args.source)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_dxf(spec), encoding="ascii", newline="\n")
    print(f"Wrote {destination}: {inspect_dxf(destination)}")


if __name__ == "__main__":
    main()
