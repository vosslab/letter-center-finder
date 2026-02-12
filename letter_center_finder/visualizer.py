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
