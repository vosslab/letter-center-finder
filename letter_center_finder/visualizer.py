"""
Generate diagnostic visualizations (PNG/SVG).

Creates multi-panel plots showing glyph, contour, hull, and fitted ellipse.
"""

import numpy
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse as MPLEllipse
from matplotlib.patches import Polygon
from typing import Dict


def create_diagnostic_plot(
	glyph_mask: numpy.ndarray,
	contour_points: numpy.ndarray,
	hull_vertices: numpy.ndarray,
	ellipse_params: Dict,
	output_path: str,
	character: str
) -> None:
	"""
	Create multi-panel diagnostic visualization.

	Args:
		glyph_mask: Binary glyph image
		contour_points: Nx2 array of contour coordinates
		hull_vertices: Mx2 array of hull vertices
		ellipse_params: Ellipse parameters dict
		output_path: Path to save PNG
		character: Character being analyzed ('O' or 'C')

	Panels:
		1. Original glyph bitmap
		2. Contour points + convex hull overlay
		3. Glyph + fitted ellipse overlay
		4. All together: glyph + hull + ellipse
	"""
	fig, axes = plt.subplots(2, 2, figsize=(12, 12))
	fig.suptitle(f'Character: {character}', fontsize=16, fontweight='bold')

	# Panel 1: Original glyph bitmap
	ax = axes[0, 0]
	ax.imshow(glyph_mask, cmap='gray', origin='upper')
	ax.set_title('Original Glyph Bitmap')
	ax.axis('off')

	# Panel 2: Contour points + convex hull
	ax = axes[0, 1]
	ax.imshow(glyph_mask, cmap='gray', origin='upper', alpha=0.3)
	ax.plot(contour_points[:, 0], contour_points[:, 1], 'g.', markersize=1, label='Contour')
	if len(hull_vertices) > 0:
		hull_polygon = Polygon(hull_vertices, fill=False, edgecolor='blue', linewidth=2, label='Convex Hull')
		ax.add_patch(hull_polygon)
	ax.set_title('Contour + Convex Hull')
	ax.legend()
	ax.axis('equal')

	# Panel 3: Glyph + fitted ellipse
	ax = axes[1, 0]
	ax.imshow(glyph_mask, cmap='gray', origin='upper', alpha=0.3)
	_draw_ellipse_on_axis(ax, ellipse_params, 'red', 'Fitted Ellipse')
	ax.set_title('Glyph + Fitted Ellipse')
	ax.legend()
	ax.axis('equal')

	# Panel 4: All together
	ax = axes[1, 1]
	ax.imshow(glyph_mask, cmap='gray', origin='upper', alpha=0.3)
	ax.plot(contour_points[:, 0], contour_points[:, 1], 'g.', markersize=1, label='Contour')
	if len(hull_vertices) > 0:
		hull_polygon = Polygon(hull_vertices, fill=False, edgecolor='blue', linewidth=2, label='Hull')
		ax.add_patch(hull_polygon)
	_draw_ellipse_on_axis(ax, ellipse_params, 'red', 'Ellipse')
	ax.set_title('Complete Overlay')
	ax.legend()
	ax.axis('equal')

	# Add text summary
	summary_text = (
		f"Center: ({ellipse_params['center'][0]:.1f}, {ellipse_params['center'][1]:.1f})\n"
		f"Major axis (vertical): {ellipse_params['major_axis']:.2f}\n"
		f"Minor axis (horizontal): {ellipse_params['minor_axis']:.2f}\n"
		f"Area: {ellipse_params['area']:.2f}\n"
		f"Eccentricity: {ellipse_params['eccentricity']:.3f}"
	)
	fig.text(0.5, 0.02, summary_text, ha='center', fontsize=10, family='monospace',
		bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

	plt.tight_layout(rect=[0, 0.08, 1, 0.96])
	plt.savefig(output_path, dpi=150, bbox_inches='tight')
	plt.close()


def _draw_ellipse_on_axis(ax, ellipse_params: Dict, color: str, label: str) -> None:
	"""
	Draw ellipse on matplotlib axis.

	Args:
		ax: Matplotlib axis
		ellipse_params: Ellipse parameters dict
		color: Color for ellipse
		label: Label for legend
	"""
	center = ellipse_params['center']
	# Note: matplotlib Ellipse takes width and height (full axes), not semi-axes
	# Our params are semi-axes, so we need to double them
	width = 2 * ellipse_params['minor_axis']  # horizontal
	height = 2 * ellipse_params['major_axis']  # vertical

	ellipse = MPLEllipse(
		xy=center,
		width=width,
		height=height,
		angle=0,  # No rotation (axis-aligned)
		fill=False,
		edgecolor=color,
		linewidth=2,
		label=label
	)
	ax.add_patch(ellipse)


def draw_ellipse_svg(
	ellipse_params: Dict,
	output_path: str,
	canvas_size: tuple = (200, 200)
) -> None:
	"""
	Export fitted ellipse as SVG for visualization.

	Args:
		ellipse_params: Ellipse parameters dict
		output_path: Path to save SVG file
		canvas_size: (width, height) of SVG canvas

	Creates clean SVG with just the ellipse shape.
	"""
	rx = ellipse_params['minor_axis']  # horizontal radius
	ry = ellipse_params['major_axis']  # vertical radius

	# Translate center to canvas center
	canvas_cx = canvas_size[0] / 2
	canvas_cy = canvas_size[1] / 2

	svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_size[0]}" height="{canvas_size[1]}" viewBox="0 0 {canvas_size[0]} {canvas_size[1]}">
	<ellipse cx="{canvas_cx}" cy="{canvas_cy}" rx="{rx}" ry="{ry}"
		fill="none" stroke="red" stroke-width="2"/>
	<circle cx="{canvas_cx}" cy="{canvas_cy}" r="3" fill="blue"/>
</svg>'''

	with open(output_path, 'w') as f:
		f.write(svg_content)


def create_diagnostic_svg_overlay(
	svg_input_path: str,
	character_results: list,
	output_path: str
) -> None:
	"""
	Create diagnostic SVG with ellipse overlays on original SVG.

	Args:
		svg_input_path: Path to original SVG file
		character_results: List of character analysis results (from pipeline)
		output_path: Path to save diagnostic SVG

	Creates an SVG with the original content plus an overlay group showing:
	- Fitted ellipses (dashed)
	- Center points (filled circles)
	- Vertical and horizontal alignment guides
	"""
	import xml.etree.ElementTree as ET

	# Read original SVG
	tree = ET.parse(svg_input_path)  # nosec B314 - local SVG files only
	root = tree.getroot()

	# Define colors for different characters (cycling through a palette)
	colors = ['#3a86ff', '#ffbe0b', '#2a9d8f', '#8338ec', '#fb5607', '#06ffa5']

	# Create overlay group
	svg_ns = 'http://www.w3.org/2000/svg'

	# Register namespace to avoid ns0 prefix
	ET.register_namespace('', svg_ns)

	# Create diagnostic overlay group
	overlay_group = ET.SubElement(root, f'{{{svg_ns}}}g')
	overlay_group.set('id', 'codex-glyph-bond-diagnostic-overlay')
	overlay_group.set('fill', 'none')
	overlay_group.set('stroke-linecap', 'round')
	overlay_group.set('stroke-linejoin', 'round')

	# Import font metric helpers
	from . import svg_parser as _sp

	# Add diagnostic elements for each character
	for idx, char_result in enumerate(character_results):
		if 'error' in char_result:
			continue

		svg_pos = char_result['svg_position']
		font_size = char_result['font']['size']
		char = char_result['char']

		# Use pre-computed SVG-space center from parser
		svg_cx = svg_pos['cx']
		svg_cy = svg_pos['cy']

		# Ellipse size from font metrics
		advance = _sp._glyph_char_advance(font_size, char)
		top_y, bottom_y = _sp._glyph_char_vertical_bounds(0, font_size, char)
		width = advance
		height = bottom_y - top_y
		if char == 'C':
			svg_rx = max(0.3, width * 0.35)
			svg_ry = max(0.3, height * 0.43)
		elif char == 'O':
			svg_rx = max(0.3, width * 0.47)
			svg_ry = max(0.3, height * 0.53)
		else:
			svg_rx = max(0.3, width * 0.40)
			svg_ry = max(0.3, height * 0.48)

		color = colors[idx % len(colors)]

		# Create group for this character
		char_group = ET.SubElement(overlay_group, f'{{{svg_ns}}}g')
		char_group.set('id', f'codex-label-diag-{idx + 1}')

		# Add ellipse (dashed)
		ellipse_elem = ET.SubElement(char_group, f'{{{svg_ns}}}ellipse')
		ellipse_elem.set('cx', f'{svg_cx:.6f}')
		ellipse_elem.set('cy', f'{svg_cy:.6f}')
		ellipse_elem.set('rx', f'{svg_rx:.6f}')
		ellipse_elem.set('ry', f'{svg_ry:.6f}')
		ellipse_elem.set('stroke', color)
		ellipse_elem.set('stroke-width', '0.25')
		ellipse_elem.set('stroke-opacity', '0.75')
		ellipse_elem.set('stroke-dasharray', '2 1')

		# Add center point
		center_circle = ET.SubElement(char_group, f'{{{svg_ns}}}circle')
		center_circle.set('cx', f'{svg_cx:.6f}')
		center_circle.set('cy', f'{svg_cy:.6f}')
		center_circle.set('r', '1.0')
		center_circle.set('fill', color)
		center_circle.set('fill-opacity', '0.7')
		center_circle.set('stroke', color)
		center_circle.set('stroke-width', '0.3')

	# Write to output file
	tree.write(output_path, encoding='utf-8', xml_declaration=True)
