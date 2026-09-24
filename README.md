# ACT knee brace DXF trials

This project reads the ACT order export for CF-1904 / Taylor Mezzanine and
creates four **trial** DXFs for `UKNBRC_1`, `UKNBRC_2`, `HUKNBRC_1`, and
`HUKNBRC_2`. The XML order gives the exact component lengths and punch
coordinates. Pages 7–10 of the punch-pattern PDF independently show the same
rounded values and identify the left and right flanges. The order confirmation
lists these pieces on lines 16–19.

```powershell
python -m brace_dxf.versioned generate samples output
python -m brace_dxf.materials samples config/boost_materials.json output/boost_materials_V8.json
python -m unittest discover -s tests -v
```

The four sample JSON files contain the ACT dimensions needed to regenerate the
DXFs. If the original order export is available locally, refresh them first with
`python -m brace_dxf.import_order 'Source Files/LOHA1046597470 Order.txt' samples`.
The customer order exports and photos are not included in this repository.
Python's standard library is sufficient to regenerate the JSON and DXFs.
The optional ACT/Boost reference PNG uses Pillow and can be regenerated with
`python -m brace_dxf.overlay samples/UKNBRC_1.json output/UKNBRC_1_V7_ACT_Boost_overlay.png`.
It plots the four ACT punch positions over the V7 finished contour at the same
inch scale; the punch circles are references, not cut holes.
The generator compares all four files with the latest version and creates the
next shared V number only when their DXF content changes. It never overwrites a
versioned file. **V8 is the current trial.**

| Version | Geometry |
| --- | --- |
| V1 | First stepped flat-pattern trial |
| V2 | Diagonal exterior with lengthwise cuts |
| V3 | Rectangular exterior and reference guides |
| V4 | Vertical cuts tangent to reference circles |
| V5 | Bend lines stop at vertical cut stations |
| V6 | Red cuts connected vertically across each web end |
| V7 | One closed finished contour on `CUT`; all guides on `REFERENCE` |
| V8 | Same finished contour; only the `CUT` layer and one closed polyline |

Current files are named `UKNBRC_1_V8.dxf`, `UKNBRC_2_V8.dxf`, and so on.
The older descriptive filenames remain in the local working folder for editor
tabs already open. The repository contains the numbered V1–V8 DXFs. V7 retains
the source blank and punch/bend guides for visual reference. V8 contains only
the finished cut. The older `*_V7_CUT_ONLY.dxf` companions are geometrically
the same as V8; the new default generator makes the cut-only form directly.

## What comes from ACT

All four pieces are 4 in × 2.5 in, 14 ga Cee. Each flange has two 5/8 in
holes, 1.25 in from its web side. Longitudinal hole positions and the full
precision member length and 14 ga designation are imported from the order XML.
The punch PDF shows
the standard Cee return lips but does not dimension them.

## Trial flat-pattern assumptions

- Each return lip is **assumed 7/8 in**, per the user's current trial value.
  The actual lip is determined by the coil and rollforming setup.
- Nominal flat width is 0.875 + 2.5 + 4 + 2.5 + 0.875 = **10.75 in**. This
  ignores thickness, inside bend radius, and bend allowance. It is therefore
  not a developed manufacturing width.
- The source blank is a full rectangle on `REFERENCE`. The finished part has
  one closed `CUT` contour. At each end, the two L-shaped cuts are joined by a
  vertical segment across the web end. The contour continues along the long
  upper and lower outside edges to close the shape. There are no
  diagonal outside edges. Each L-cut turns across its flange at the inboard
  tangent of the nearby 5/8 in reference circle, 0.3125 in from its center. Its lengthwise
  run is provisionally 0.125 in outside the web/flange bend line. The punch
  circles and their transverse center guides are **reference geometry only**.
  These cut offsets are **not dimensioned in the ACT source files**.
- The web extends the complete ACT member length. The trial has no developed
  bend radii, corner reliefs, or kerf compensation.

V8 contains just the single closed `CUT` contour. V7 retains a `REFERENCE`
layer with the original rectangular blank, four ACT punch circles, four
transverse center guides, and two yellow dashed bend lines. The bend lines stop
at the adjacent vertical cut stations. The ACI colors are trial settings in
each JSON file; Boost compatibility and operation mapping still need confirmation.

## Material lookup

The ACT order says **14 ga** for these four pieces. The user confirmed Boost
material **1.0038** (Steel) and raw material **STAI0080** for this trial. The
editable lookup in `config/boost_materials.json` uses a provisional 0.0785 in
nominal galvanized 14 ga thickness and records STAI0080 as 0.080 in. The
selector chooses the smallest configured raw-material thickness at least as
large as the nominal gauge thickness. Add more verified gauge and Boost table
rows to that file later. The nominal value follows the
[Ferraz Shawmut sheet-metal gauge chart](https://fsconnect.ferrazshawmut.com/marketing/PDFs/BEI-Bookmarked.pdf);
it has not been checked against the Unravel Android app or the actual coil
measurement.

`output/boost_materials_V8.json` records the resulting selection for each part.
It is a selection guide, not a DXF import setting: the DXFs do **not** fill
Boost's Material or Raw Material fields automatically. Assign those fields in
Boost until a tested Boost-specific import or automation path is available.

## Boost import observation for V7

When both layers were brought into Boost, **Automatic** outline processing
reported that the outer contour was not processed. Boost showed the original
rectangular blank outside the finished stepped contour. Setting **Cut geometry
→ Outline → No outline** removed that warning in the user's import and Boost
then displayed a cutting program. The larger closed rectangle on `REFERENCE`
is the likely cause of the automatic outline ambiguity; this is an inference
from the screen and has not been isolated with a cut-only import. The
V8 removes the rectangle and all other reference entities without changing
the finished contour. Inspect the generated cut path before use; V8's Boost
Automatic outline import has not yet been confirmed.

## Known-good Boost comparison

`output/uncoiler payoff stand side plate.DXF` is a user-supplied file that
imports well in Boost. It uses DXF AC1021, has no declared drawing units,
and contains 45 LINE and 43 ARC entities. Its entities carry explicit ACI 7
color on layers `0` and `1`. The brace V8 files use inch units and one finished
LWPOLYLINE on `CUT` only. The different color
setup may explain Boost's reported element-color warning, but that has not
been confirmed by an import comparison.

The photos establish the general end shape, but perspective and installed
hardware do not establish a reliable cut dimension. A dimensioned flat
pattern, lip and bend data, or a confirmed existing blank is still needed
before fabrication.
