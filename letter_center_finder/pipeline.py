"""
End-to-end processing orchestration.

Coordinates parsing, rendering, fitting, and visualization.
"""

import os
import json
import glob
from typing import Dict

from . import svg_parser
from . import glyph_renderer
from . import geometry
from . import visualizer


def process_single_character(
	char_metadata: Dict,
	output_dir: str,
	char_index: int = 0,
	scale_factor: int = 4,
	verbose: bool = False
) -> Dict:
	"""
	Process one character: render -> fit -> visualize.

	Args:
		char_metadata: Character metadata from SVG parser
		output_dir: Directory for output files
		char_index: Index of this character (for naming)
		scale_factor: Rendering scale factor
		verbose: Print verbose output

	Returns:
		Dict with all analysis results
	"""
	char = char_metadata['character']

	if verbose:
		print(f"  Processing {char} #{char_index}...")

	try:
		# Render glyph
		glyph_image = glyph_renderer.render_single_glyph(
			char,
			char_metadata['font_size'],
			char_metadata.get('font_family', 'sans-serif'),
			char_metadata.get('font_weight', 'normal'),
			scale_factor
		)

		# Extract binary mask
		binary_mask = glyph_renderer.extract_binary_mask(glyph_image)

		# Extract contour points
		contour_points = glyph_renderer.extract_contour_points(binary_mask)

		# Compute convex hull
		hull_result = geometry.compute_convex_hull(contour_points)

		# Fit ellipse
		ellipse_result = geometry.fit_axis_aligned_ellipse(contour_points)

		# Compute fit quality
		fit_quality = geometry.compute_fit_quality(contour_points, ellipse_result)

		# Generate diagnostic plot
		output_filename = f"{char}_{char_index}_diagnostic.png"
		output_path = os.path.join(output_dir, output_filename)
		visualizer.create_diagnostic_plot(
			binary_mask,
			contour_points,
			hull_result['vertices'],
			ellipse_result,
			output_path,
			char
		)

		if verbose:
			print(f"    ✓ Saved diagnostic: {output_filename}")

		# Compile results
		result = {
			'char': char,
			'index': char_index,
			'svg_position': {
				'x': char_metadata['x'],
				'y': char_metadata['y']
			},
			'font': {
				'family': char_metadata.get('font_family', 'sans-serif'),
				'size': char_metadata['font_size'],
				'weight': char_metadata.get('font_weight', 'normal')
			},
			'convex_hull': {
				'vertices': hull_result['vertices'].tolist(),
				'area': hull_result['area'],
				'perimeter': hull_result['perimeter']
			},
			'ellipse': ellipse_result,
			'fit_quality': fit_quality,
			'diagnostic_file': output_filename
		}

		return result

	except Exception as e:
		if verbose:
			print(f"    ✗ Error processing {char} #{char_index}: {e}")
		return {
			'char': char,
			'index': char_index,
			'error': str(e)
		}


def process_svg_file(
	svg_path: str,
	output_dir: str,
	target_letters: str = 'OC',
	scale_factor: int = 4,
	verbose: bool = False
) -> Dict:
	"""
	Process all O/C characters in one SVG file.

	Args:
		svg_path: Path to SVG file
		output_dir: Output directory
		target_letters: Letters to analyze (e.g., 'OC')
		scale_factor: Rendering scale factor
		verbose: Print verbose output

	Returns:
		Dict with processing results
	"""
	svg_basename = os.path.splitext(os.path.basename(svg_path))[0]

	if verbose:
		print(f"\nProcessing: {svg_basename}")

	# Create output subdirectory
	svg_output_dir = os.path.join(output_dir, svg_basename)
	os.makedirs(svg_output_dir, exist_ok=True)

	# Parse SVG
	try:
		all_chars = svg_parser.parse_svg_file(svg_path)
	except Exception as e:
		if verbose:
			print(f"  ✗ Error parsing SVG: {e}")
		return {
			'svg_file': svg_basename,
			'error': f"Parse error: {e}",
			'characters': []
		}

	# Filter for target letters
	target_chars = [c for c in all_chars if c['character'] in target_letters]

	if verbose:
		print(f"  Found {len(target_chars)} target characters ({target_letters})")

	# Process each character
	results = []
	char_counts = {}

	for char_meta in target_chars:
		char = char_meta['character']
		char_index = char_counts.get(char, 0)
		char_counts[char] = char_index + 1

		result = process_single_character(
			char_meta,
			svg_output_dir,
			char_index,
			scale_factor,
			verbose
		)
		results.append(result)

	# Save results JSON
	results_data = {
		'svg_file': svg_basename,
		'characters': results
	}

	results_path = os.path.join(svg_output_dir, 'results.json')
	with open(results_path, 'w') as f:
		json.dump(results_data, f, indent=2)

	if verbose:
		print(f"  ✓ Saved results: {results_path}")

	# Generate summary text
	summary_path = os.path.join(svg_output_dir, 'summary.txt')
	_write_summary_text(summary_path, results_data)

	if verbose:
		print(f"  ✓ Saved summary: {summary_path}")

	return results_data


def batch_process(
	input_dir: str,
	output_dir: str,
	target_letters: str = 'OC',
	scale_factor: int = 4,
	verbose: bool = False
) -> Dict:
	"""
	Process all SVG files in directory.

	Args:
		input_dir: Directory containing SVG files
		output_dir: Output directory
		target_letters: Letters to analyze
		scale_factor: Rendering scale factor
		verbose: Print verbose output

	Returns:
		Dict with aggregate statistics
	"""
	# Find all SVG files
	svg_pattern = os.path.join(input_dir, '*.svg')
	svg_files = glob.glob(svg_pattern)

	if len(svg_files) == 0:
		print(f"No SVG files found in {input_dir}")
		return {'error': 'No SVG files found', 'files_processed': 0}

	if verbose:
		print(f"Found {len(svg_files)} SVG files")

	# Create output directory
	os.makedirs(output_dir, exist_ok=True)

	# Process each file
	all_results = []
	for svg_path in sorted(svg_files):
		result = process_svg_file(
			svg_path,
			output_dir,
			target_letters,
			scale_factor,
			verbose
		)
		all_results.append(result)

	# Aggregate statistics
	total_chars = sum(len(r.get('characters', [])) for r in all_results)
	successful_chars = sum(
		len([c for c in r.get('characters', []) if 'error' not in c])
		for r in all_results
	)

	stats = {
		'files_processed': len(svg_files),
		'total_characters': total_chars,
		'successful_characters': successful_chars,
		'failed_characters': total_chars - successful_chars
	}

	# Write summary report
	summary_report_path = os.path.join(output_dir, 'summary_report.txt')
	with open(summary_report_path, 'w') as f:
		f.write("Letter Glyph Analysis Summary\n")
		f.write("=" * 50 + "\n\n")
		f.write(f"Files processed: {stats['files_processed']}\n")
		f.write(f"Total characters analyzed: {stats['total_characters']}\n")
		f.write(f"Successful: {stats['successful_characters']}\n")
		f.write(f"Failed: {stats['failed_characters']}\n\n")

		for result in all_results:
			f.write(f"\n{result['svg_file']}:\n")
			f.write(f"  Characters: {len(result.get('characters', []))}\n")

	if verbose:
		print(f"\n✓ Summary report: {summary_report_path}")

	return stats


def _write_summary_text(output_path: str, results_data: Dict) -> None:
	"""
	Write human-readable summary text.

	Args:
		output_path: Path to summary file
		results_data: Results dict
	"""
	with open(output_path, 'w') as f:
		f.write(f"Analysis Results: {results_data['svg_file']}\n")
		f.write("=" * 60 + "\n\n")

		for char_result in results_data['characters']:
			if 'error' in char_result:
				f.write(f"{char_result['char']} #{char_result['index']}: ERROR - {char_result['error']}\n\n")
				continue

			char = char_result['char']
			idx = char_result['index']
			ellipse = char_result['ellipse']
			hull = char_result['convex_hull']
			fit = char_result['fit_quality']

			f.write(f"{char} #{idx}:\n")
			f.write(f"  SVG Position: ({char_result['svg_position']['x']:.2f}, {char_result['svg_position']['y']:.2f})\n")
			f.write(f"  Font: {char_result['font']['family']} {char_result['font']['size']}pt {char_result['font']['weight']}\n")
			f.write("\n  Ellipse:\n")
			f.write(f"    Center: ({ellipse['center'][0]:.2f}, {ellipse['center'][1]:.2f})\n")
			f.write(f"    Major axis (vertical): {ellipse['major_axis']:.2f}\n")
			f.write(f"    Minor axis (horizontal): {ellipse['minor_axis']:.2f}\n")
			f.write(f"    Area: {ellipse['area']:.2f}\n")
			f.write(f"    Eccentricity: {ellipse['eccentricity']:.4f}\n")
			f.write("\n  Convex Hull:\n")
			f.write(f"    Area: {hull['area']:.2f}\n")
			f.write(f"    Perimeter: {hull['perimeter']:.2f}\n")
			f.write("\n  Fit Quality:\n")
			f.write(f"    RMSE: {fit['rmse']:.4f}\n")
			f.write(f"    Max error: {fit['max_error']:.4f}\n")
			f.write(f"    Coverage: {fit['coverage']:.2%}\n")
			f.write(f"\n  Diagnostic: {char_result['diagnostic_file']}\n")
			f.write("\n" + "-" * 60 + "\n\n")
