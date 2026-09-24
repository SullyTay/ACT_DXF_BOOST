"""Render a dimensionally aligned ACT punch / Boost cut reference image."""

import argparse
from pathlib import Path
import sys

from .__main__ import finished_outline, inner_cut_paths, load_spec, outline


def render(spec_path, destination):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        local_deps = Path(__file__).resolve().parents[1] / ".deps"
        if local_deps.is_dir():
            sys.path.insert(0, str(local_deps))
            try:
                from PIL import Image, ImageDraw, ImageFont
            except ImportError as local_exc:
                raise SystemExit("Pillow is needed to render the PNG overlay") from local_exc
        else:
            raise SystemExit("Pillow is needed to render the PNG overlay") from exc

    spec = load_spec(spec_path)
    scale_factor = 2
    width_px, height_px = 1800, 900
    image = Image.new("RGB", (width_px * scale_factor, height_px * scale_factor),
                      "#f7f9fc")
    draw = ImageDraw.Draw(image)
    font_file = Path("C:/Windows/Fonts/segoeui.ttf")
    bold_file = Path("C:/Windows/Fonts/segoeuib.ttf")

    def font(size, bold=False):
        path = bold_file if bold else font_file
        return ImageFont.truetype(str(path), size * scale_factor)

    def point(x, y):
        left = 105
        right = 1695
        bottom = 725
        units_per_inch = (right - left) / spec["length"]
        return (round((left + x * units_per_inch) * scale_factor),
                round((bottom - y * units_per_inch) * scale_factor))

    def box(x0, y0, x1, y1, **kwargs):
        draw.rectangle((x0 * scale_factor, y0 * scale_factor,
                        x1 * scale_factor, y1 * scale_factor), **kwargs)

    def text(x, y, value, color="#263445", size=22, bold=False, anchor="lt"):
        draw.text((x * scale_factor, y * scale_factor), value,
                  fill=color, font=font(size, bold), anchor=anchor)

    def dashed(a, b, color, dash=10, gap=8, line_width=2):
        from math import hypot

        distance = hypot(b[0] - a[0], b[1] - a[1])
        if distance == 0:
            return
        run = 0
        while run < distance:
            end = min(run + dash * scale_factor, distance)
            p = (a[0] + (b[0] - a[0]) * run / distance,
                 a[1] + (b[1] - a[1]) * run / distance)
            q = (a[0] + (b[0] - a[0]) * end / distance,
                 a[1] + (b[1] - a[1]) * end / distance)
            draw.line((p, q), fill=color, width=line_width * scale_factor)
            run += (dash + gap) * scale_factor

    text(105, 35, f"{spec['piece_mark']}  |  ACT punch layout + Boost V7 cut profile",
         size=34, bold=True)
    text(105, 90, "Aligned by ACT length and flange position  •  dimensions in inches",
         size=19, color="#586779")

    # The ACT source blank is only a reference; Boost's finished contour is blue.
    blank = outline(spec)
    cut = finished_outline(spec)
    draw.polygon([point(x, y) for x, y in cut], fill="#5189ad")
    cut_points = [point(x, y) for x, y in cut]
    draw.line(cut_points + cut_points[:1], fill="#13b74f", width=5 * scale_factor,
              joint="curve")
    for a, b in zip(blank, blank[1:] + blank[:1]):
        dashed(point(*a), point(*b), "#8793a1", 11, 9)

    # Bend guides use ACT's web/flange boundaries and end at the tangent cuts.
    paths = inner_cut_paths(spec)
    bend_ys = (spec["trial_lip_width"] + spec["flange_width"],
               spec["trial_lip_width"] + spec["flange_width"]
               + spec["web_width"])
    for y, near, far in ((bend_ys[0], paths[0][2][0], paths[1][2][0]),
                         (bend_ys[1], paths[2][2][0], paths[3][2][0])):
        dashed(point(near, y), point(far, y), "#f9d437", 13, 10, 3)

    hole_radius = spec["hole_diameter"] / 2
    hole_y = {"left": bend_ys[1] + spec["hole_offset_from_web"],
              "right": bend_ys[0] - spec["hole_offset_from_web"]}
    pixel_radius = round(hole_radius * (1590 / spec["length"]) * scale_factor)
    for side in ("left", "right"):
        for hole_x in spec["holes"][side]:
            cx, cy = point(hole_x, hole_y[side])
            draw.ellipse((cx - pixel_radius, cy - pixel_radius,
                          cx + pixel_radius, cy + pixel_radius),
                         outline="#db3131", width=3 * scale_factor)
            cross = 6 * scale_factor
            draw.line((cx - cross, cy, cx + cross, cy),
                      fill="#db3131", width=2 * scale_factor)
            draw.line((cx, cy - cross, cx, cy + cross),
                      fill="#db3131", width=2 * scale_factor)
            x_label, _ = point(hole_x, 0)
            label_y = 238 if side == "left" else 774
            text(x_label / scale_factor, label_y, f"{hole_x:.3f}",
                 color="#b62222", size=19, bold=True, anchor="mt")
            marker_y = 277 if side == "left" else 751
            dashed((x_label, marker_y * scale_factor),
                   (x_label, (cy - pixel_radius - 4 * scale_factor)
                    if side == "left" else (cy + pixel_radius + 4 * scale_factor)),
                   "#da7b7b", 4, 7, 1)

    text(118, 164, "ACT FLANGE LEFT", size=21, bold=True, color="#b62222")
    text(118, 755, "ACT FLANGE RIGHT", size=21, bold=True, color="#b62222")
    text(1450, 490, "WEB", size=24, bold=True, color="#f8fdff")
    text(105, 825, f"ACT overall length  {spec['length']:.3f} in", size=21,
         color="#263445", bold=True)

    # A compact legend makes the cut and reference status clear in the export.
    box(100, 126, 1698, 159, fill="#e9eef4")
    draw.line((125 * scale_factor, 143 * scale_factor,
               167 * scale_factor, 143 * scale_factor),
              fill="#13b74f", width=5 * scale_factor)
    text(178, 130, "Boost V7 CUT", size=17)
    draw.ellipse((461 * scale_factor, 136 * scale_factor,
                  477 * scale_factor, 152 * scale_factor),
                 outline="#db3131", width=2 * scale_factor)
    text(492, 130, "ACT hole reference (not cut)", size=17)
    dashed((870 * scale_factor, 143 * scale_factor),
           (915 * scale_factor, 143 * scale_factor), "#8793a1", 6, 4)
    text(929, 130, "Original blank", size=17)
    dashed((1198 * scale_factor, 143 * scale_factor),
           (1243 * scale_factor, 143 * scale_factor), "#f9d437", 6, 4, 3)
    text(1258, 130, "Bend reference", size=17)

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.resize((width_px, height_px), Image.Resampling.LANCZOS).save(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec")
    parser.add_argument("output")
    args = parser.parse_args()
    print(render(args.spec, args.output))


if __name__ == "__main__":
    main()
