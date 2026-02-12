# CHANGELOG

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- `docs/PROJECT_GOALS.md`: project goals, strategies (v1 failed, v2 planned),
  failure analysis, and quantitative measures of success
- Complete implementation of letter glyph ellipse fitting system
- `letter_center_finder/` Python package with five core modules:
  - `svg_parser.py`: Parse SVG files and extract O and C character metadata
  - `glyph_renderer.py`: Render isolated characters as clean bitmaps using PIL
  - `geometry.py`: Compute convex hull and fit axis-aligned ellipses
  - `visualizer.py`: Generate diagnostic PNG visualizations with matplotlib
  - `pipeline.py`: End-to-end processing orchestration for single files and batch processing
- `find_letter_centers.py`: Command-line interface for processing SVG files
- Comprehensive test suite with 32 unit tests covering all modules
- Support for extracting O and C characters from complex SVG text elements including tspans
- Axis-aligned ellipse fitting using variance-based approach (vertical major axis, horizontal minor axis)
- Convex hull computation with area and perimeter metrics
- Multi-panel diagnostic visualizations showing glyph, contour, hull, and fitted ellipse
- Batch processing of multiple SVG files with aggregate statistics
- JSON and human-readable text output formats
- `pip_requirements.txt`: numpy, opencv-python, pillow, scipy, matplotlib

### Changed
- Fixed package initialization file typo: `__init_.py` -> `__init__.py`

### Implementation Details
- Uses PIL/Pillow for high-quality glyph rendering with anti-aliasing
- Uses OpenCV for binary mask extraction and contour detection
- Uses scipy.spatial.ConvexHull for robust hull computation
- Ellipse semi-axis calculation: `semi_axis = sqrt(2) * std_dev` for points uniformly distributed on ellipse
- Supports font metadata extraction (family, size, weight) from SVG text and tspan elements
- Handles CSS style attributes in SVG parsing
- Scale factor parameter (default 4x) for high-resolution rendering

### Verification
- All 32 custom unit tests pass
- All code quality tests pass (pyflakes, indentation, shebangs, import star)
- Successfully processed 6 target SVG files with 44 total characters
- Generated diagnostic visualizations and results for all test cases
