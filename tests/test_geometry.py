import unittest
from pathlib import Path

from brace_dxf.__main__ import (
    bend_spans, build_dxf, finished_outline, inner_cut_paths, load_spec, outline,
)
from brace_dxf.import_order import read_braces


ROOT = Path(__file__).resolve().parents[1]
SPECS = [load_spec(path) for path in sorted((ROOT / "samples").glob("*.json"))]


def inside_polygon(point, vertices):
    x, y = point
    inside = False
    for start, end in zip(vertices, vertices[1:] + vertices[:1]):
        x0, y0 = start
        x1, y1 = end
        if (y0 > y) != (y1 > y):
            crossing = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < crossing:
                inside = not inside
    return inside


class TrialGeometryTest(unittest.TestCase):
    def test_reference_circle_extents_remain_inside_outer_outline(self):
        for spec in SPECS:
            perimeter = outline(spec)
            radius = spec["hole_diameter"] / 2
            flange = spec["flange_width"]
            web = spec["web_width"]
            lip = spec["trial_lip_width"]
            offset = spec["hole_offset_from_web"]
            for side, y in (("right", lip + flange - offset),
                            ("left", lip + flange + web + offset)):
                for x in spec["holes"][side]:
                    with self.subTest(mark=spec["piece_mark"], side=side, x=x):
                        for point in ((x, y), (x - radius, y), (x + radius, y),
                                      (x, y - radius), (x, y + radius)):
                            self.assertTrue(inside_polygon(point, perimeter), point)

    def test_web_runs_full_length(self):
        for spec in SPECS:
            perimeter = outline(spec)
            midpoint = spec["trial_lip_width"] + spec["flange_width"] + spec["web_width"] / 2
            for x in (0.001, spec["length"] / 2, spec["length"] - 0.001):
                self.assertTrue(inside_polygon((x, midpoint), perimeter))

    def test_outer_outline_is_a_full_rectangle(self):
        for spec in SPECS:
            width = 2 * spec["trial_lip_width"] + 2 * spec["flange_width"] + spec["web_width"]
            self.assertEqual(outline(spec), [(0, 0), (spec["length"], 0),
                                             (spec["length"], width), (0, width)])

    def test_output_has_inch_units_and_closed_perimeter(self):
        for spec in SPECS:
            dxf = build_dxf(spec)
            self.assertIn("9\n$INSUNITS\n70\n1\n", dxf)
            self.assertIn("0\nLWPOLYLINE\n100\nAcDbEntity\n8\nCUT\n100\nAcDbPolyline\n90\n12\n70\n1\n", dxf)
            self.assertIn("0\nLWPOLYLINE\n100\nAcDbEntity\n8\nREFERENCE\n100\nAcDbPolyline\n90\n4\n70\n1\n", dxf)

    def test_cut_only_companion_has_one_closed_contour_and_no_references(self):
        for spec in SPECS:
            dxf = build_dxf(spec, include_reference=False)
            self.assertEqual(dxf.count("0\nLWPOLYLINE\n"), 1)
            self.assertIn("8\nCUT\n100\nAcDbPolyline\n90\n12\n70\n1\n", dxf)
            self.assertNotIn("REFERENCE", dxf)
            self.assertNotIn("0\nCIRCLE\n", dxf)
            self.assertNotIn("0\nLINE\n", dxf)

    def test_sample_data_matches_act_order(self):
        source = ROOT / "Source Files" / "LOHA1046597470 Order.txt"
        if not source.exists():
            self.skipTest("Original ACT order export is not included in the repository")
        imported = read_braces(source)
        for spec in SPECS:
            self.assertEqual(spec, imported[spec["piece_mark"]])

    def test_lengthwise_cuts_reach_the_exterior_and_leave_holes_as_references(self):
        for spec in SPECS:
            paths = inner_cut_paths(spec)
            self.assertEqual(len(paths), 4)
            lip = spec["trial_lip_width"]
            flange = spec["flange_width"]
            web = spec["web_width"]
            full_width = 2 * lip + 2 * flange + web
            clearance = spec["trial_cut_clearance_from_bend"]
            for side, pair, root_y, cut_y, outer_y in (
                ("right", paths[:2], lip + flange, lip + flange - clearance, 0),
                ("left", paths[2:], lip + flange + web,
                 lip + flange + web + clearance, full_width),
            ):
                near, far = spec["holes"][side]
                near_cut, far_cut = pair
                with self.subTest(mark=spec["piece_mark"], side=side):
                    self.assertEqual(near_cut[0], (0, root_y))
                    self.assertEqual(far_cut[0], (spec["length"], root_y))
                    self.assertEqual(near_cut[1], (0, cut_y))
                    self.assertEqual(far_cut[1], (spec["length"], cut_y))
                    self.assertEqual(near_cut[2][1], cut_y)
                    self.assertEqual(far_cut[2][1], cut_y)
                    self.assertEqual(near_cut[3][1], outer_y)
                    self.assertEqual(far_cut[3][1], outer_y)
                    self.assertLess(near, near_cut[2][0])
                    self.assertLess(far_cut[2][0], far)
                    self.assertAlmostEqual(
                        near_cut[2][0] - near, spec["hole_diameter"] / 2)
                    self.assertAlmostEqual(
                        far - far_cut[2][0], spec["hole_diameter"] / 2)
            dxf = build_dxf(spec)
            self.assertEqual(dxf.count("8\nREFERENCE\n100\nAcDbCircle\n"), 4)
            self.assertEqual(dxf.count("8\nREFERENCE\n100\nAcDbLine\n"), 4)
            self.assertEqual(dxf.count("8\nREFERENCE\n62\n2\n6\nDASHED\n100\nAcDbLine\n"), 2)
            self.assertNotIn("INNER_CUT", dxf)
            self.assertNotIn("CONSTRUCTION", dxf)

    def test_finished_cut_is_one_closed_rectilinear_contour(self):
        for spec in SPECS:
            contour = finished_outline(spec)
            self.assertEqual(len(contour), 12)
            segments = list(zip(contour, contour[1:] + contour[:1]))
            self.assertTrue(all(a != b and (a[0] == b[0] or a[1] == b[1])
                                for a, b in segments))
            paths = inner_cut_paths(spec)
            bottom_y = paths[0][2][1]
            top_y = paths[2][2][1]
            width = outline(spec)[2][1]
            self.assertIn(((0, top_y), (0, bottom_y)), segments)
            self.assertIn(((spec["length"], bottom_y),
                           (spec["length"], top_y)), segments)
            self.assertIn(((paths[0][2][0], 0), (paths[1][2][0], 0)), segments)
            self.assertIn(((paths[3][2][0], width),
                           (paths[2][2][0], width)), segments)

    def test_bend_lines_stop_at_the_vertical_cut_stations(self):
        for spec in SPECS:
            paths = inner_cut_paths(spec)
            spans = bend_spans(paths)
            self.assertEqual(len(spans), 2)
            for near_cut, far_cut, (x_start, y, x_end) in (
                (paths[0], paths[1], spans[0]),
                (paths[2], paths[3], spans[1]),
            ):
                with self.subTest(mark=spec["piece_mark"], y=y):
                    self.assertEqual(x_start, near_cut[2][0])
                    self.assertEqual(x_end, far_cut[2][0])
                    self.assertEqual(y, near_cut[0][1])
                    self.assertEqual(y, far_cut[0][1])
                    self.assertLess(x_start, x_end)


if __name__ == "__main__":
    unittest.main()
