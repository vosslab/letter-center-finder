"""
Generate diagnostic visualizations (PNG and SVG).

Creates multi-panel plots showing the isolation render, binary mask,
contour with convex hull, and fitted ellipse overlay.
"""

import numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot
import matplotlib.patches
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"


#============================================
def create_diagnostic_plot(
	glyph_image: numpy.ndarray,
	binary_mask: numpy.ndarray,
	contour_points: numpy.ndarray,
	hull_vertices: numpy.ndarray,
	ellipse_params: dict,
	fit_quality: dict,
	output_path: str,
	character: str,
) -> None:
	"""
	Create multi-panel diagnostic PNG for one glyph.

	Panels:
		1. Isolation render (grayscale image of just the glyph)
		2. Binary mask after thresholding
		3. Contour (green) + convex hull (blue) on the glyph
		4. All overlays: contour + hull + fitted ellipse (red)

	Args:
		glyph_image: Grayscale rendered image (cropped to glyph region)
		binary_mask: Binary mask (cropped to glyph region)
		contour_points: Nx2 contour coordinates (in cropped space)
		hull_vertices: Mx2 hull vertices (in cropped space)
		ellipse_params: Ellipse dict with center, semi_x, semi_y
		fit_quality: Fit quality metrics dict
		output_path: Path to save the PNG
		character: Character label ('O' or 'C')
	"""
	fig, axes = matplotlib.pyplot.subplots(2, 2, figsize=(12, 12))
	fig.suptitle(f"Character: {character}", fontsize=16, fontweight='bold')

	# Panel 1: Isolation render
	ax = axes[0, 0]
	ax.imshow(glyph_image, cmap='gray', origin='upper')
	ax.set_title('Isolation Render')
	ax.axis('off')

	# Panel 2: Binary mask
	ax = axes[0, 1]
	ax.imshow(binary_mask, cmap='gray', origin='upper')
	ax.set_title('Binary Mask')
	ax.axis('off')

	# Panel 3: Contour + convex hull
	ax = axes[1, 0]
	ax.imshow(glyph_image, cmap='gray', origin='upper', alpha=0.3)
	ax.plot(contour_points[:, 0], contour_points[:, 1],
		'g.', markersize=1, label='Contour')
	if len(hull_vertices) > 0:
		hull_poly = matplotlib.patches.Polygon(
			hull_vertices, fill=False, edgecolor='blue',
			linewidth=2, label='Convex Hull'
		)
		ax.add_patch(hull_poly)
	ax.set_title('Contour + Convex Hull')
	ax.legend(fontsize=8)
	ax.set_aspect('equal')

	# Panel 4: All overlays including fitted ellipse
	ax = axes[1, 1]
	ax.imshow(glyph_image, cmap='gray', origin='upper', alpha=0.3)
	ax.plot(contour_points[:, 0], contour_points[:, 1],
		'g.', markersize=1, label='Contour')
	if len(hull_vertices) > 0:
		hull_poly = matplotlib.patches.Polygon(
			hull_vertices, fill=False, edgecolor='blue',
			linewidth=1.5, label='Hull', linestyle='--'
		)
		ax.add_patch(hull_poly)
	# Draw fitted ellipse
	_draw_ellipse_on_axis(ax, ellipse_params, 'red', 'Fitted Ellipse')
	# Draw center marker
	cx, cy = ellipse_params['center']
	ax.plot(cx, cy, 'r+', markersize=12, markeredgewidth=2, label='Center')
	ax.set_title('Ellipse Fit Overlay')
	ax.legend(fontsize=8)
	ax.set_aspect('equal')

	# Summary text below plots
	summary = (
		f"Center: ({cx:.1f}, {cy:.1f})  "
		f"Semi-X: {ellipse_params['semi_x']:.1f}  "
		f"Semi-Y: {ellipse_params['semi_y']:.1f}  "
		f"Eccentricity: {ellipse_params['eccentricity']:.3f}\n"
		f"Center offset: {fit_quality['center_offset_pct']:.1f}%  "
		f"Mean boundary: {fit_quality['mean_boundary_pct']:.1f}%  "
		f"Max boundary: {fit_quality['max_boundary_pct']:.1f}%  "
		f"Coverage: {fit_quality['coverage']:.1%}"
	)
	fig.text(0.5, 0.02, summary, ha='center', fontsize=9, family='monospace',
		bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

	matplotlib.pyplot.tight_layout(rect=[0, 0.06, 1, 0.96])
	matplotlib.pyplot.savefig(output_path, dpi=150, bbox_inches='tight')
	matplotlib.pyplot.close()


#============================================
def _draw_ellipse_on_axis(ax, ellipse_params: dict, color: str, label: str) -> None:
	"""
	Draw an axis-aligned ellipse on a matplotlib axis.

	Args:
		ax: Matplotlib axis
		ellipse_params: Ellipse dict with center, semi_x, semi_y
		color: Color for the ellipse
		label: Legend label
	"""
	cx, cy = ellipse_params['center']
	# matplotlib Ellipse takes full width/height, not semi-axes
	width = 2.0 * ellipse_params['semi_x']
	height = 2.0 * ellipse_params['semi_y']

	ellipse = matplotlib.patches.Ellipse(
		xy=(cx, cy), width=width, height=height,
		angle=0, fill=False, edgecolor=color, linewidth=2, label=label
	)
	ax.add_patch(ellipse)


#============================================
def create_diagnostic_svg_overlay(
	svg_input_path: str,
	character_results: list,
	output_path: str,
) -> None:
	"""
	Create diagnostic SVG with ellipse overlays on the original SVG.

	Overlays fitted ellipses and center markers at the SVG-space positions
	computed by mapping pixel coordinates back through the viewBox transform.

	Args:
		svg_input_path: Path to the original SVG file
		character_results: List of result dicts from the pipeline
		output_path: Path to save the diagnostic SVG
	"""
	tree = ET.parse(svg_input_path)  # nosec B314 - local SVG files only
	root = tree.getroot()

	ET.register_namespace('', SVG_NS)

	# Create overlay group
	overlay = ET.SubElement(root, f'{{{SVG_NS}}}g')
	overlay.set('id', 'ellipse-fit-overlay')
	overlay.set('fill', 'none')

	# Color palette for different characters
	colors = ['#ff3333', '#3366ff', '#33cc33', '#ff9900', '#cc33ff', '#00cccc']

	for idx, result in enumerate(character_results):
		if 'error' in result:
			continue

		svg_ellipse = result.get('svg_ellipse')
		if svg_ellipse is None:
			continue

		color = colors[idx % len(colors)]
		char = result['char']
		cx = svg_ellipse['cx']
		cy = svg_ellipse['cy']
		rx = svg_ellipse['rx']
		ry = svg_ellipse['ry']

		# Group for this character
		grp = ET.SubElement(overlay, f'{{{SVG_NS}}}g')
		grp.set('id', f'fit-{char}-{idx}')

		# Ellipse outline
		ell = ET.SubElement(grp, f'{{{SVG_NS}}}ellipse')
		ell.set('cx', f'{cx:.4f}')
		ell.set('cy', f'{cy:.4f}')
		ell.set('rx', f'{rx:.4f}')
		ell.set('ry', f'{ry:.4f}')
		ell.set('stroke', color)
		ell.set('stroke-width', '0.4')
		ell.set('stroke-opacity', '0.85')
		ell.set('fill', 'none')

		# Center dot
		dot = ET.SubElement(grp, f'{{{SVG_NS}}}circle')
		dot.set('cx', f'{cx:.4f}')
		dot.set('cy', f'{cy:.4f}')
		dot.set('r', '0.8')
		dot.set('fill', color)
		dot.set('fill-opacity', '0.8')

	tree.write(output_path, encoding='utf-8', xml_declaration=True)
