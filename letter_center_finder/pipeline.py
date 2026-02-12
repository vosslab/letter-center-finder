"""
End-to-end processing orchestration.

Coordinates SVG parsing, per-character isolation rendering, ellipse fitting,
coordinate mapping, and diagnostic visualization.
"""

import os
import json
import glob

import numpy

from . import svg_parser
from . import glyph_renderer
from . import geometry
from . import visualizer


#============================================
def process_single_character(
	svg_path: str,
	char_meta: dict,
	svg_dims: dict,
	output_dir: str,
	char_index: int = 0,
	zoom: int = 10,
	verbose: bool = False,
) -> dict:
	"""
	Process one character: isolate, render, fit, visualize.

	Args:
		svg_path: Path to original SVG file
		char_meta: Character metadata from svg_parser
		svg_dims: SVG dimensions dict from get_svg_dimensions
		output_dir: Directory for output files
		char_index: Index of this character (for output naming)
		zoom: Render zoom factor
		verbose: Print progress

	Returns:
		Dict with all analysis results including SVG-space ellipse
	"""
	char = char_meta['character']

	if verbose:
		print(f"  Processing {char} #{char_index} "
			f"(source: {char_meta['source_text'][:30]})")

	# Step 1: Render isolated glyph
	glyph_image = glyph_renderer.render_isolated_glyph(svg_path, char_meta, zoom)

	# Step 2: Extract binary mask
	binary_mask = glyph_renderer.extract_binary_mask(glyph_image)

	# Step 3: Check that we actually found glyph pixels
	glyph_pixel_count = numpy.count_nonzero(binary_mask)
	if glyph_pixel_count < 10:
		error_msg = f"Too few glyph pixels ({glyph_pixel_count}), isolation may have failed"
		if verbose:
			print(f"    x {error_msg}")
		return {'char': char, 'index': char_index, 'error': error_msg}

	# Step 4: Crop to glyph region for efficiency and better diagnostics
	glyph_crop, mask_crop, crop_offset = _crop_to_glyph(glyph_image, binary_mask, padding=20)

	# Step 5: Extract contour in cropped coordinates
	contour_points = glyph_renderer.extract_contour_points(mask_crop)

	# Step 6: Compute convex hull
	hull_result = geometry.compute_convex_hull(contour_points)

	# Step 7: Fit ellipse
	# For C glyphs, use convex hull to close the opening
	if char == 'C':
		fit_points = hull_result['vertices']
	else:
		fit_points = contour_points
	ellipse_result = geometry.fit_axis_aligned_ellipse(fit_points)

	# Step 8: Compute fit quality against the full contour
	fit_quality = geometry.compute_fit_quality(contour_points, ellipse_result)

	# Step 9: Map ellipse center from cropped-pixel space to SVG space
	# First map from cropped to full-image pixel space
	pixel_cx = ellipse_result['center'][0] + crop_offset[0]
	pixel_cy = ellipse_result['center'][1] + crop_offset[1]
	# Then map from pixel space to SVG space
	svg_cx, svg_cy = svg_parser.pixel_to_svg(pixel_cx, pixel_cy, svg_dims, zoom)

	# Map semi-axes from pixel to SVG units (use scale factor)
	vb = svg_dims['viewBox']
	vp_w = svg_dims['viewport_width'] * zoom
	scale = min(vp_w / vb['width'],
		svg_dims['viewport_height'] * zoom / vb['height'])
	svg_rx = ellipse_result['semi_x'] / scale
	svg_ry = ellipse_result['semi_y'] / scale

	svg_ellipse = {
		'cx': float(svg_cx),
		'cy': float(svg_cy),
		'rx': float(svg_rx),
		'ry': float(svg_ry),
	}

	# Step 10: Generate diagnostic PNG
	diag_filename = f"{char}_{char_index}_diagnostic.png"
	diag_path = os.path.join(output_dir, diag_filename)
	visualizer.create_diagnostic_plot(
		glyph_crop, mask_crop, contour_points,
		hull_result['vertices'], ellipse_result, fit_quality,
		diag_path, char
	)

	if verbose:
		print(f"    + Saved diagnostic: {diag_filename}")
		print(f"    SVG center: ({svg_cx:.2f}, {svg_cy:.2f})")
		print(f"    Mean boundary: {fit_quality['mean_boundary_pct']:.1f}%  "
			f"Coverage: {fit_quality['coverage']:.1%}")

	# Compile results
	result = {
		'char': char,
		'index': char_index,
		'svg_position': {
			'x': char_meta['x'],
			'y': char_meta['y'],
			'cx': char_meta['cx'],
			'cy': char_meta['cy'],
		},
		'font': {
			'family': char_meta.get('font_family', 'sans-serif'),
			'size': char_meta['font_size'],
			'weight': char_meta.get('font_weight', 'normal'),
		},
		'pixel_ellipse': {
			'center': ellipse_result['center'],
			'semi_x': ellipse_result['semi_x'],
			'semi_y': ellipse_result['semi_y'],
		},
		'svg_ellipse': svg_ellipse,
		'convex_hull': {
			'area': hull_result['area'],
			'perimeter': hull_result['perimeter'],
			'num_vertices': len(hull_result['vertices']),
		},
		'ellipse': ellipse_result,
		'fit_quality': fit_quality,
		'diagnostic_file': diag_filename,
	}

	return result


#============================================
def _crop_to_glyph(image: numpy.ndarray, mask: numpy.ndarray,
	padding: int = 20) -> tuple:
	"""
	Crop image and mask to the glyph bounding box with padding.

	Args:
		image: Grayscale image
		mask: Binary mask (255 = glyph)
		padding: Pixels of padding around the glyph

	Returns:
		Tuple of (cropped_image, cropped_mask, (x_offset, y_offset))
	"""
	# Find bounding box of non-zero pixels in the mask
	coords = numpy.column_stack(numpy.where(mask > 0))
	if len(coords) == 0:
		return image, mask, (0, 0)

	y_min, x_min = coords.min(axis=0)
	y_max, x_max = coords.max(axis=0)

	# Add padding, clamped to image bounds
	y_min = max(0, y_min - padding)
	x_min = max(0, x_min - padding)
	y_max = min(image.shape[0], y_max + padding + 1)
	x_max = min(image.shape[1], x_max + padding + 1)

	cropped_image = image[y_min:y_max, x_min:x_max]
	cropped_mask = mask[y_min:y_max, x_min:x_max]

	return cropped_image, cropped_mask, (x_min, y_min)


#============================================
def process_svg_file(
	svg_path: str,
	output_dir: str,
	target_letters: str = 'OC',
	zoom: int = 10,
	verbose: bool = False,
) -> dict:
	"""
	Process all O/C characters in one SVG file.

	Args:
		svg_path: Path to SVG file
		output_dir: Output directory
		target_letters: Letters to analyze (e.g., 'OC')
		zoom: Render zoom factor
		verbose: Print progress

	Returns:
		Dict with processing results for all characters
	"""
	svg_basename = os.path.splitext(os.path.basename(svg_path))[0]

	if verbose:
		print(f"\nProcessing: {svg_basename}")

	# Create output subdirectory
	svg_output_dir = os.path.join(output_dir, svg_basename)
	os.makedirs(svg_output_dir, exist_ok=True)

	# Get SVG dimensions for coordinate mapping
	svg_dims = svg_parser.get_svg_dimensions(svg_path)

	# Parse SVG to find target characters
	all_chars = svg_parser.parse_svg_file(svg_path)
	target_chars = [c for c in all_chars if c['character'] in target_letters]

	if verbose:
		print(f"  Found {len(target_chars)} target characters ({target_letters})")

	# Process each character
	results = []
	char_counts = {}

	for char_meta in target_chars:
		char = char_meta['character']
		char_idx = char_counts.get(char, 0)
		char_counts[char] = char_idx + 1

		result = process_single_character(
			svg_path, char_meta, svg_dims, svg_output_dir,
			char_idx, zoom, verbose
		)
		results.append(result)

	# Save results JSON
	results_data = {
		'svg_file': svg_basename,
		'characters': results,
	}

	results_path = os.path.join(svg_output_dir, 'results.json')
	with open(results_path, 'w') as f:
		json.dump(results_data, f, indent=2)

	if verbose:
		print(f"  + Saved results: {results_path}")

	# Generate summary text
	summary_path = os.path.join(svg_output_dir, 'summary.txt')
	_write_summary_text(summary_path, results_data)

	# Generate diagnostic SVG overlay
	diag_svg_path = os.path.join(svg_output_dir, f'{svg_basename}_diagnostic.svg')
	visualizer.create_diagnostic_svg_overlay(svg_path, results, diag_svg_path)

	if verbose:
		print(f"  + Saved diagnostic SVG: {diag_svg_path}")

	return results_data


#============================================
def batch_process(
	input_dir: str,
	output_dir: str,
	target_letters: str = 'OC',
	zoom: int = 10,
	verbose: bool = False,
) -> dict:
	"""
	Process all SVG files in a directory.

	Args:
		input_dir: Directory containing SVG files
		output_dir: Output directory
		target_letters: Letters to analyze
		zoom: Render zoom factor
		verbose: Print progress

	Returns:
		Dict with aggregate statistics
	"""
	svg_pattern = os.path.join(input_dir, '*.svg')
	svg_files = sorted(glob.glob(svg_pattern))

	if len(svg_files) == 0:
		print(f"No SVG files found in {input_dir}")
		return {'error': 'No SVG files found', 'files_processed': 0}

	if verbose:
		print(f"Found {len(svg_files)} SVG files")

	os.makedirs(output_dir, exist_ok=True)

	all_results = []
	for svg_path in svg_files:
		result = process_svg_file(
			svg_path, output_dir, target_letters, zoom, verbose
		)
		all_results.append(result)

	# Aggregate statistics
	total_chars = sum(len(r.get('characters', [])) for r in all_results)
	successful = sum(
		len([c for c in r.get('characters', []) if 'error' not in c])
		for r in all_results
	)

	stats = {
		'files_processed': len(svg_files),
		'total_characters': total_chars,
		'successful_characters': successful,
		'failed_characters': total_chars - successful,
	}

	# Write summary report
	report_path = os.path.join(output_dir, 'summary_report.txt')
	with open(report_path, 'w') as f:
		f.write("Letter Glyph Ellipse Fitting Summary\n")
		f.write("=" * 50 + "\n\n")
		f.write(f"Files processed: {stats['files_processed']}\n")
		f.write(f"Total characters: {stats['total_characters']}\n")
		f.write(f"Successful: {stats['successful_characters']}\n")
		f.write(f"Failed: {stats['failed_characters']}\n\n")

		for result in all_results:
			f.write(f"\n{result['svg_file']}:\n")
			for char_result in result.get('characters', []):
				if 'error' in char_result:
					f.write(f"  {char_result['char']} #{char_result['index']}: "
						f"ERROR - {char_result['error']}\n")
				else:
					svg_e = char_result['svg_ellipse']
					fq = char_result['fit_quality']
					f.write(f"  {char_result['char']} #{char_result['index']}: "
						f"center=({svg_e['cx']:.2f}, {svg_e['cy']:.2f}) "
						f"rx={svg_e['rx']:.2f} ry={svg_e['ry']:.2f} "
						f"boundary={fq['mean_boundary_pct']:.1f}%\n")

	if verbose:
		print(f"\n+ Summary report: {report_path}")

	return stats


#============================================
def _write_summary_text(output_path: str, results_data: dict) -> None:
	"""
	Write human-readable summary for one SVG file.

	Args:
		output_path: Path to summary file
		results_data: Results dict
	"""
	with open(output_path, 'w') as f:
		f.write(f"Analysis Results: {results_data['svg_file']}\n")
		f.write("=" * 60 + "\n\n")

		for cr in results_data['characters']:
			if 'error' in cr:
				f.write(f"{cr['char']} #{cr['index']}: ERROR - {cr['error']}\n\n")
				continue

			char = cr['char']
			idx = cr['index']
			svg_e = cr['svg_ellipse']
			fq = cr['fit_quality']
			ell = cr['ellipse']

			f.write(f"{char} #{idx}:\n")
			f.write(f"  SVG Ellipse Center: ({svg_e['cx']:.3f}, {svg_e['cy']:.3f})\n")
			f.write(f"  SVG Semi-Axes: rx={svg_e['rx']:.3f}  ry={svg_e['ry']:.3f}\n")
			f.write(f"  Eccentricity: {ell['eccentricity']:.4f}\n")
			f.write(f"  Convex Hull Area: {cr['convex_hull']['area']:.1f} px^2\n")
			f.write(f"  Fit Quality:\n")
			f.write(f"    Center offset: {fq['center_offset_pct']:.2f}%\n")
			f.write(f"    Mean boundary dist: {fq['mean_boundary_pct']:.2f}%\n")
			f.write(f"    Max boundary dist: {fq['max_boundary_pct']:.2f}%\n")
			f.write(f"    Coverage: {fq['coverage']:.1%}\n")
			f.write(f"  Diagnostic: {cr['diagnostic_file']}\n")
			f.write("\n" + "-" * 60 + "\n\n")
