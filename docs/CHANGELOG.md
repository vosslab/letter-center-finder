# CHANGELOG

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- `docs/INSTALL.md`: setup steps, system dependencies (librsvg), Python
  requirements, and verify command
- `docs/USAGE.md`: CLI reference, examples, and input/output documentation
- `docs/PROJECT_GOALS.md`: project goals, strategies (v1 failed, v2 implemented),
  failure analysis, and quantitative measures of success
- `README.md`: rewrote with overview, quick start, doc links, and status

### Changed (v2 Rewrite -- Per-Character SVG Isolation)
- Rewrote `glyph_renderer.py`: replaced PIL isolated rendering with
  per-character SVG color isolation and `rsvg-convert` rendering. For each
  target glyph, all SVG elements except the target character are set to white,
  then the SVG is rendered at high resolution with native fonts.
- Rewrote `geometry.py`: replaced `std * sqrt(2)` ellipse fitting with direct
  least-squares axis-aligned conic fitting. Added proper geometric distance
  metrics (center offset, mean/max boundary distance, coverage).
- Rewrote `pipeline.py`: new workflow using isolation SVGs, pixel-to-SVG
  coordinate mapping via viewBox transform, and per-character diagnostic output.
- Rewrote `visualizer.py`: new 4-panel diagnostic PNGs (isolation render,
  binary mask, contour+hull, ellipse overlay) and SVG overlay with measured
  ellipse positions.
- Updated `svg_parser.py`: added `get_svg_dimensions()`, `svg_to_pixel()`,
  `pixel_to_svg()` for viewBox coordinate mapping. Added element identification
  fields (`_text_elem_index`, `_tspan_index`, `_char_offset`) to character
  metadata for the isolation SVG builder.
- Updated `find_letter_centers.py`: replaced `--scale` with `--zoom` flag
  for `rsvg-convert` zoom factor (default 10).
- C glyphs now fit to convex hull vertices to close the opening, giving
  a better ellipse approximation for the open shape.

### Results
- All 6 SVG files processed, 44 characters total, 0 failures
- O glyphs: 1.3-1.6% mean boundary distance, 92-100% coverage
- C glyphs: 11.4% mean boundary distance (convex hull), 98-99% coverage
- All code quality tests pass (pyflakes, ASCII, indentation, shebangs)

### Previous Implementation (v1 -- Failed)
- Initial implementation using PIL isolated rendering with system fonts
- Used variance-based ellipse fitting (`semi_axis = sqrt(2) * std_dev`)
- All 6 SVG files had bad fits: wrong centers, wrong sizes, wrong positions
- See [docs/PROJECT_GOALS.md](PROJECT_GOALS.md) for detailed failure analysis
