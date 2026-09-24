import copy
import unittest
from pathlib import Path

from brace_dxf.materials import build_manifest, load_lookup, select_material


ROOT = Path(__file__).resolve().parents[1]


class MaterialLookupTest(unittest.TestCase):
    def test_14_gauge_braces_select_user_confirmed_boost_material(self):
        manifest = build_manifest(ROOT / "samples", ROOT / "config/boost_materials.json")
        self.assertEqual(len(manifest["assignments"]), 4)
        for row in manifest["assignments"]:
            self.assertEqual(row["act_gauge"], 14)
            self.assertEqual(row["boost_material"], "1.0038")
            self.assertEqual(row["boost_raw_material"], "STAI0080")
            self.assertGreaterEqual(row["boost_raw_thickness_in"],
                                    row["nominal_thickness_in"])

    def test_lookup_chooses_closest_thickness_not_below_nominal(self):
        lookup = load_lookup(ROOT / "config/boost_materials.json")
        lookup = copy.deepcopy(lookup)
        lookup["available_raw_materials"] = [
            {"code": "TOO_THIN", "thickness_in": 0.07},
            {"code": "THICKER", "thickness_in": 0.09},
            {"code": "CLOSEST", "thickness_in": 0.08},
        ]
        result = select_material({"piece_mark": "TEST", "gauge": 14}, lookup)
        self.assertEqual(result["boost_raw_material"], "CLOSEST")


if __name__ == "__main__":
    unittest.main()
