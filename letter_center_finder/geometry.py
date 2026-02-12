"""
Compute convex hull and fit axis-aligned ellipses.

Uses direct least-squares fitting for axis-aligned ellipses and
scipy.spatial.ConvexHull for hull computation.
"""

import numpy
import scipy.spatial


#============================================
def compute_convex_hull(points: numpy.ndarray) -> dict:
	"""
	Compute convex hull of a point set.

	Args:
		points: Nx2 array of (x, y) coordinates

	Returns:
		Dict with:
		- vertices: Mx2 array of hull vertex coordinates
		- area: hull area in square pixels
		- perimeter: hull perimeter in pixels
	"""
	if len(points) < 3:
		raise ValueError("Need at least 3 points to compute convex hull")

	hull = scipy.spatial.ConvexHull(points)

	# Extract hull vertices in order
	hull_vertices = points[hull.vertices]

	# Compute perimeter by summing edge lengths
	perimeter = 0.0
	n_verts = len(hull_vertices)
	for i in range(n_verts):
		p1 = hull_vertices[i]
		p2 = hull_vertices[(i + 1) % n_verts]
		perimeter += numpy.linalg.norm(p2 - p1)

	return {
		'vertices': hull_vertices,
		'area': float(hull.volume),  # In 2D, volume attribute gives area
		'perimeter': float(perimeter),
	}


#============================================
def fit_axis_aligned_ellipse(points: numpy.ndarray) -> dict:
	"""
	Fit an axis-aligned ellipse using direct least-squares.

	Fits the conic equation: a*x^2 + b*y^2 + c*x + d*y + 1 = 0
	via ordinary least squares.

	The ellipse has no rotation (axis-aligned), with semi_x as the
	horizontal semi-axis and semi_y as the vertical semi-axis.

	Args:
		points: Nx2 array of (x, y) coordinates (contour or hull points)

	Returns:
		Dict with:
		- center: [cx, cy] pixel coordinates
		- semi_x: horizontal semi-axis length
		- semi_y: vertical semi-axis length
		- major_axis: larger semi-axis (should be vertical for O/C)
		- minor_axis: smaller semi-axis (should be horizontal for O/C)
		- area: pi * semi_x * semi_y
		- eccentricity: sqrt(1 - (minor/major)^2)
	"""
	if len(points) < 5:
		raise ValueError("Need at least 5 points to fit ellipse")

	x = points[:, 0].astype(float)
	y = points[:, 1].astype(float)

	# Build design matrix for: a*x^2 + b*y^2 + c*x + d*y = -1
	design = numpy.column_stack([x**2, y**2, x, y])
	rhs = -numpy.ones(len(x))

	# Solve via least squares
	result, _, _, _ = numpy.linalg.lstsq(design, rhs, rcond=None)
	a_coeff, b_coeff, c_coeff, d_coeff = result

	# Validate: for a valid ellipse, a and b must be positive
	if a_coeff <= 0 or b_coeff <= 0:
		return _fallback_ellipse_fit(points)

	# Extract center: cx = -c/(2a), cy = -d/(2b)
	cx = -c_coeff / (2.0 * a_coeff)
	cy = -d_coeff / (2.0 * b_coeff)

	# Semi-axes: R = c^2/(4a) + d^2/(4b) - 1
	r_val = c_coeff**2 / (4.0 * a_coeff) + d_coeff**2 / (4.0 * b_coeff) - 1.0

	if r_val <= 0:
		return _fallback_ellipse_fit(points)

	semi_x = numpy.sqrt(r_val / a_coeff)
	semi_y = numpy.sqrt(r_val / b_coeff)

	# Determine major/minor (major should be the larger one)
	major_axis = max(semi_x, semi_y)
	minor_axis = min(semi_x, semi_y)

	# Eccentricity
	if major_axis > 0:
		eccentricity = numpy.sqrt(1.0 - (minor_axis / major_axis) ** 2)
	else:
		eccentricity = 0.0

	return {
		'center': [float(cx), float(cy)],
		'semi_x': float(semi_x),
		'semi_y': float(semi_y),
		'major_axis': float(major_axis),
		'minor_axis': float(minor_axis),
		'area': float(numpy.pi * semi_x * semi_y),
		'eccentricity': float(eccentricity),
	}


#============================================
def _fallback_ellipse_fit(points: numpy.ndarray) -> dict:
	"""
	Fallback ellipse fit using bounding box when least-squares fails.

	Uses the centroid as center and half the bounding box extent as
	semi-axes.

	Args:
		points: Nx2 array of (x, y) coordinates

	Returns:
		Ellipse parameter dict (same format as fit_axis_aligned_ellipse)
	"""
	cx = float(numpy.mean(points[:, 0]))
	cy = float(numpy.mean(points[:, 1]))
	semi_x = float((numpy.max(points[:, 0]) - numpy.min(points[:, 0])) / 2.0)
	semi_y = float((numpy.max(points[:, 1]) - numpy.min(points[:, 1])) / 2.0)

	major_axis = max(semi_x, semi_y)
	minor_axis = min(semi_x, semi_y)

	if major_axis > 0:
		eccentricity = numpy.sqrt(1.0 - (minor_axis / major_axis) ** 2)
	else:
		eccentricity = 0.0

	return {
		'center': [cx, cy],
		'semi_x': semi_x,
		'semi_y': semi_y,
		'major_axis': major_axis,
		'minor_axis': minor_axis,
		'area': float(numpy.pi * semi_x * semi_y),
		'eccentricity': float(eccentricity),
	}


#============================================
def _point_to_ellipse_distance(px: float, py: float, cx: float, cy: float,
	semi_x: float, semi_y: float) -> float:
	"""
	Approximate distance from a point to the nearest point on an ellipse.

	Uses the algebraic distance scaled by the local radius for a
	fast approximation. Exact geometric distance requires iterative
	root finding and is overkill for quality metrics.

	Args:
		px, py: Point coordinates
		cx, cy: Ellipse center
		semi_x, semi_y: Horizontal and vertical semi-axes

	Returns:
		Approximate distance in pixels
	"""
	# Normalize to unit circle space
	dx = (px - cx) / semi_x
	dy = (py - cy) / semi_y
	# Distance from origin to point in normalized space
	r_norm = numpy.sqrt(dx**2 + dy**2)
	if r_norm == 0:
		# Point is at center, distance is the minor semi-axis
		return min(semi_x, semi_y)
	# Angle of the point
	theta = numpy.arctan2(dy * semi_x, dx * semi_y)
	# Radius of ellipse at this angle
	cos_t = numpy.cos(theta)
	sin_t = numpy.sin(theta)
	r_ellipse = (semi_x * semi_y) / numpy.sqrt(
		(semi_y * cos_t)**2 + (semi_x * sin_t)**2
	)
	# Point radius at this angle
	r_point = numpy.sqrt((px - cx)**2 + (py - cy)**2)
	return abs(r_point - r_ellipse)


#============================================
def compute_fit_quality(points: numpy.ndarray, ellipse: dict) -> dict:
	"""
	Measure quality of ellipse fit against contour points.

	Computes meaningful geometric metrics rather than algebraic distances.

	Args:
		points: Nx2 array of (x, y) contour coordinates
		ellipse: Ellipse parameters dict from fit_axis_aligned_ellipse

	Returns:
		Dict with:
		- center_offset: distance from ellipse center to point centroid
		- center_offset_pct: center_offset normalized by average semi-axis
		- mean_boundary_dist: avg distance from points to ellipse boundary
		- mean_boundary_pct: normalized by average semi-axis
		- max_boundary_dist: max distance from any point to ellipse boundary
		- max_boundary_pct: normalized by average semi-axis
		- coverage: fraction of points inside or on the ellipse
	"""
	cx, cy = ellipse['center']
	semi_x = ellipse['semi_x']
	semi_y = ellipse['semi_y']
	avg_radius = (semi_x + semi_y) / 2.0

	if avg_radius == 0:
		return _degenerate_quality()

	# Center offset: distance from ellipse center to centroid of points
	centroid_x = float(numpy.mean(points[:, 0]))
	centroid_y = float(numpy.mean(points[:, 1]))
	center_offset = numpy.sqrt((cx - centroid_x)**2 + (cy - centroid_y)**2)

	# Boundary distance for each point
	distances = numpy.array([
		_point_to_ellipse_distance(p[0], p[1], cx, cy, semi_x, semi_y)
		for p in points
	])

	mean_dist = float(numpy.mean(distances))
	max_dist = float(numpy.max(distances))

	# Coverage: fraction of points inside the ellipse (algebraic test)
	x_norm = (points[:, 0] - cx) / semi_x
	y_norm = (points[:, 1] - cy) / semi_y
	ellipse_vals = x_norm**2 + y_norm**2
	# Points on or inside the ellipse have value <= 1.0
	# Allow small tolerance for points very close to boundary
	coverage = float(numpy.sum(ellipse_vals <= 1.05) / len(points))

	return {
		'center_offset': float(center_offset),
		'center_offset_pct': float(center_offset / avg_radius * 100.0),
		'mean_boundary_dist': mean_dist,
		'mean_boundary_pct': float(mean_dist / avg_radius * 100.0),
		'max_boundary_dist': max_dist,
		'max_boundary_pct': float(max_dist / avg_radius * 100.0),
		'coverage': coverage,
	}


#============================================
def _degenerate_quality() -> dict:
	"""Return quality metrics for a degenerate (zero-radius) ellipse."""
	return {
		'center_offset': float('inf'),
		'center_offset_pct': float('inf'),
		'mean_boundary_dist': float('inf'),
		'mean_boundary_pct': float('inf'),
		'max_boundary_dist': float('inf'),
		'max_boundary_pct': float('inf'),
		'coverage': 0.0,
	}
