# Usage

Analyze O and C letter glyphs in SVG chemical structure diagrams. The tool
parses SVG text elements, isolates each target glyph by color masking, renders
with `rsvg-convert`, fits an axis-aligned ellipse, and generates diagnostic
output.

## Quick start

```bash
python find_letter_centers.py -i targets/ -o output/
```

This processes all SVG files in `targets/` and writes results to `output/`.

## CLI

Entry point: [find_letter_centers.py](../find_letter_centers.py)

| Flag | Default | Description |
|---|---|---|
| `-i`, `--input` | `targets/` | Input SVG file or directory |
| `-o`, `--output` | `output/` | Output directory for results |
| `-l`, `--letters` | `OC` | Letters to analyze |
| `-z`, `--zoom` | `10` | SVG render zoom factor for rsvg-convert |
| `-v`, `--verbose` | off | Verbose output |

## Examples

Process a single file with verbose output:

```bash
python find_letter_centers.py -i targets/ALLLDM_furanose_alpha.svg -o output/ -v
```

Analyze only O glyphs across all target files:

```bash
python find_letter_centers.py -i targets/ -o output/ -l O
```

Higher zoom for finer rendering detail:

```bash
python find_letter_centers.py -i targets/ -o output/ -z 16
```

## Inputs and outputs

### Inputs

- SVG files containing chemical structure diagrams with `<text>` elements for
  glyph labels (O, OH, HO, C, CH2OH, etc.)
- Six sample SVGs are provided in [targets/](../targets/)

### Outputs

All output goes into the directory specified by `-o`:

- Per-glyph diagnostic PNGs (4-panel: isolation render, binary mask,
  contour with convex hull, ellipse overlay)
- Per-file SVG overlay with fitted ellipses on the original diagram
- JSON results with ellipse parameters (center, semi-axes) in SVG coordinates
- Console summary with character counts and success/failure statistics

## Known gaps

- [ ] Document JSON output schema and field definitions
- [ ] Document per-file SVG overlay naming convention
