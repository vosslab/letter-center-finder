# PROJECT_GOALS.md

Find the geometric center and fit axis-aligned ellipses to O and C letter glyphs
inside complex SVG chemical structure diagrams.

## Project Goals

1. **Locate O and C glyphs** in `targets/*.svg` files, which contain chemical
   structure diagrams with paths, polygons, lines, and multi-character text
   labels (OH, HO, CH2OH, etc.).
2. **Fit an axis-aligned ellipse** to each O and C glyph. The major axis is
   vertical and the minor axis is horizontal. O and C glyphs are never rotated.
3. **Compute the convex hull** of each glyph outline.
4. **Report the glyph center** in SVG coordinate space.
5. **Generate diagnostic PNG and SVG** visualizations that show the ellipse
   overlaid on the actual glyph, so a human can verify correctness at a glance.

## Target SVG Files

Six SVG files under [targets/](../targets/) contain chemical sugar ring
diagrams. Each SVG has:

- **Paths**: curved bond arcs with Bezier commands
- **Polygons**: colored structural wedges (dark red `#8b0000`, black `#000000`)
- **Lines**: bond connections with varying stroke widths
- **Text elements**: chemical labels such as O, OH, HO, CH2OH, with `<tspan>`
  sub-elements for subscripts

O glyphs appear as standalone bold text (12pt, dark red) at the ring oxygen
position and as part of OH/HO labels (10.8pt, black). C glyphs appear inside
compound labels like `HOH2C` as a `<tspan>` element. Font sizes range from
7.8pt (subscripts) to 12pt. Text anchors vary: start, middle, and end.

## Strategy v1 -- Isolated PIL Rendering (Failed)

### Approach

1. Parse SVG XML to find `<text>` elements containing O or C characters.
2. Estimate character position in SVG space using hardcoded font metric
   constants (advance width = 0.62 x font_size, vertical bounds =
   baseline - 0.78 x font_size to baseline + 0.16 x font_size).
3. Render each character **in isolation** onto a blank PIL canvas using a macOS
   system font (Helvetica/Arial).
4. Threshold the rendered bitmap with Otsu's method (OpenCV) to get a binary
   mask.
5. Extract the largest external contour from the binary mask.
6. Fit an axis-aligned ellipse using `semi_axis = std_dev * sqrt(2)`.
7. Overlay estimated ellipses on the original SVG using the font metric
   positions.

### Why It Failed

All six SVG files produce bad fits. Zero out of six files pass visual
inspection.

**Root cause 1 -- Font mismatch.** The PIL renderer uses a macOS system font
that does not match the font embedded or referenced by the SVG. The rendered
glyph shape differs from what appears in the SVG, so the contour is wrong from
the start.

**Root cause 2 -- Estimated positions are inaccurate.** The SVG overlay uses
hardcoded font metric ratios (`width * 0.35` for C, `width * 0.47` for O) to
place ellipses. These rough estimates do not match the actual rendered glyph
positions in any of the six test files.

**Root cause 3 -- Weak ellipse fitting.** The `std_dev * sqrt(2)` formula
assumes contour points are uniformly distributed on the ellipse boundary.
OpenCV contour points are densely sampled along edges and sparse on straight
runs. The resulting ellipse is systematically too small, and for the C glyph
(open shape), the center is pulled toward the curve and away from the geometric
center.

**Root cause 4 -- Metrics are too lenient.** The current fit quality metric
reports 43-48% coverage and RMSE values of 0.7-4.3, yet every result is marked
successful. There is no threshold that rejects a bad fit, so 100% of characters
"pass" despite none being correct.

**Root cause 5 -- No ground truth check.** The diagnostic PNGs show the fitted
ellipse on the **PIL-rendered** glyph (which is already wrong), not on the
actual SVG. There is no way to visually verify that the ellipse matches the real
glyph in the SVG.

## Strategy v2 -- Per-Character SVG Isolation and Render (Planned)

### Core Idea

For each target glyph, create a temporary SVG where the **only visible element**
is the single character we want to fit. Everything else -- paths, polygons,
lines, other text elements, and neighboring characters within the same text
element -- is set to white fill/stroke so it is invisible on the white
background. The SVG renderer (cairosvg) handles all font metrics, kerning, and
positioning natively because the original text structure is preserved. We only
change colors.

### Approach

1. **Parse SVG XML** to extract O/C text positions, font sizes, fill colors,
   and the SVG `viewBox` for coordinate mapping.
2. **For each target glyph, build an isolation SVG**:
   a. Deep-copy the original SVG DOM.
   b. Set every `<path>`, `<polygon>`, and `<line>` element to
      `fill="#ffffff"` and `stroke="#ffffff"` (invisible on white).
   c. Set every `<text>` element to `fill="#ffffff"`.
   d. For the text element containing the target character, restructure it
      with `<tspan>` wrappers so that **only the target character** retains
      its original fill color. All other characters in the same text element
      get `fill="#ffffff"`. For example, to isolate O in `<text>OH</text>`:
      ```xml
      <text><tspan fill="#000">O</tspan><tspan fill="#fff">H</tspan></text>
      ```
      Tspans without explicit position attributes inherit the parent layout,
      so character positions are preserved exactly.
   e. Write the isolation SVG to a temp file.
3. **Render the isolation SVG** to a high-resolution PNG using `cairosvg`
   (or `rsvg-convert` as fallback). The rendered image contains exactly one
   visible glyph at its correct position with the correct font.
4. **Threshold** the rendered image (Otsu's method). No segmentation or
   component filtering needed because the image contains only one glyph.
5. **Extract the outer contour** using `cv2.findContours` with
   `RETR_EXTERNAL`.
6. **Compute the convex hull** using `scipy.spatial.ConvexHull`.
7. **Fit an axis-aligned ellipse** using least-squares optimization
   (`scipy.optimize`) that minimizes the distance from contour points to the
   ellipse boundary. For the C glyph, fit to convex hull vertices to close
   the opening.
8. **Map pixel coordinates back to SVG space** using the inverse of the
   viewBox-to-raster transform, so the ellipse center and axes are reported
   in SVG coordinates.
9. **Validate fit quality** with strict metrics (see Measures of Success).
10. **Generate diagnostic output**:
    - Multi-panel PNG per glyph showing: isolation render, binary mask,
      contour with convex hull, and fitted ellipse overlay.
    - SVG overlay with fitted ellipses placed on the original diagram.

### Key Differences from v1

| Aspect | v1 (Failed) | v2 (Planned) |
|---|---|---|
| Glyph source | PIL render with system font | SVG render with native font |
| Isolation method | Render character alone (wrong font) | Hide everything except target character in SVG |
| Neighboring chars | Not a problem (isolated render) | White-filled tspans, invisible |
| Background artifacts | Not a problem (isolated render) | White-filled paths/lines/polygons, invisible |
| Position source | Estimated font metrics | Measured from rendered pixels + viewBox mapping |
| Ellipse fitting | `std * sqrt(2)` shortcut | Least-squares optimization |
| Diagnostic overlay | Estimated positions on SVG | Measured positions from render |
| Fit validation | Lenient (no rejection) | Strict thresholds with rejection |

### Tspan Splitting Details

The trickiest case is isolating a character that sits in the middle of a text
string. For example, isolating the first O in `<tspan>HOH</tspan>`:

```xml
<!-- Original -->
<tspan>HOH</tspan>

<!-- Isolation of O (index 1) -->
<tspan fill="#ffffff">H</tspan><tspan fill="#000000">O</tspan><tspan fill="#ffffff">H</tspan>
```

Each new tspan inherits the same font-family, font-size, and baseline from the
parent, so the character flow is identical. The `dy` attributes on tspans (used
for subscripts like the `2` in `CH2OH`) must be preserved on the correct split
fragment.

### Why This Solves the v1 Failures

- **Font mismatch**: eliminated. The SVG renderer uses the same font the SVG
  specifies.
- **Position inaccuracy**: eliminated. The character is rendered at its true SVG
  position. Pixel-to-SVG mapping via viewBox gives exact coordinates.
- **Background contamination**: eliminated. Every non-target element is white.
- **Adjacent letter contamination**: eliminated. Neighboring characters in the
  same text element are white-filled.

## Failures to Watch For

- **Tspan splitting edge cases**: characters with `dx`/`dy` offsets must
  preserve those attributes on the correct fragment after splitting.
- **cairosvg rendering fidelity**: some SVG features may render differently.
  Mitigation: fall back to `rsvg-convert` or Inkscape CLI.
- **Font substitution**: if the SVG references a font not installed on the
  system, the renderer will substitute. Mitigation: verify glyph shape in
  diagnostics.
- **Namespace handling**: the target SVGs use `ns0:` prefixed elements.
  The isolation SVG builder must preserve namespaces correctly.

## Measures of Success

### Hard Requirements (Must Pass)

1. **Visual match**: the diagnostic PNG for every glyph must show the fitted
   ellipse outline closely tracing the outer edge of the glyph. A human
   reviewer looking at the diagnostic should immediately agree the fit is
   correct.
2. **Center accuracy**: the ellipse center must lie within the visual center of
   the glyph. Quantitatively, the center offset (distance from ellipse center
   to contour centroid) must be less than 5% of the glyph height.
3. **Edge accuracy**: the mean distance from outer contour points to the
   nearest point on the ellipse boundary must be less than 5% of the average
   ellipse radius.
4. **All files pass**: all six SVG files in `targets/` must produce acceptable
   fits for every O and C glyph found. Zero failures allowed.

### Quantitative Metrics

| Metric | Definition | Threshold |
|---|---|---|
| Center offset | Euclidean distance from ellipse center to contour centroid, normalized by glyph height | < 5% |
| Mean boundary distance | Average distance from contour points to nearest ellipse boundary point, normalized by average radius | < 5% |
| Max boundary distance | Maximum distance from any contour point to ellipse boundary, normalized by average radius | < 15% |
| Hull coverage | Fraction of convex hull area enclosed by the ellipse | > 85% |
| Aspect ratio sanity | Major/minor axis ratio for O should be 1.0-1.4; for C should be 1.0-1.6 | Within range |

### Diagnostic Outputs

Each processed glyph must produce a multi-panel diagnostic PNG containing:

1. **Isolation render panel**: the rendered isolation SVG showing only the
   target glyph (verifies that isolation worked and the correct character is
   visible).
2. **Binary mask panel**: the thresholded binary mask of the glyph.
3. **Contour and hull panel**: the outer contour (green) and convex hull
   (blue) drawn on the glyph image.
4. **Ellipse overlay panel**: the fitted ellipse (red) with center marker
   drawn on the glyph image, alongside the contour and hull.

Each processed SVG file must also produce a diagnostic SVG with all fitted
ellipses overlaid on the original diagram.

### Test Suite

- All existing code quality tests must continue to pass (pyflakes, ASCII
  compliance, indentation, import checks).
- Unit tests must cover: SVG rendering and coordinate mapping, ROI extraction,
  glyph segmentation, ellipse fitting math, and fit quality validation.
- Integration tests must process all six `targets/*.svg` files and verify that
  every detected glyph meets the quantitative thresholds above.

## Files

### Core Modules ([letter_center_finder/](../letter_center_finder/))

- [svg_parser.py](../letter_center_finder/svg_parser.py): SVG XML parsing, text
  extraction, coordinate mapping
- [glyph_renderer.py](../letter_center_finder/glyph_renderer.py): SVG
  rasterization, ROI extraction, glyph segmentation
- [geometry.py](../letter_center_finder/geometry.py): ellipse fitting, convex
  hull, fit quality metrics
- [visualizer.py](../letter_center_finder/visualizer.py): diagnostic PNG and
  SVG generation
- [pipeline.py](../letter_center_finder/pipeline.py): end-to-end orchestration

### CLI

- [find_letter_centers.py](../find_letter_centers.py): command-line interface

### Dependencies

- [pip_requirements.txt](../pip_requirements.txt): numpy, opencv-python,
  pillow, scipy, matplotlib, cairosvg
