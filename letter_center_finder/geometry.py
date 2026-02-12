"""
Compute convex hull and fit axis-aligned ellipse.

Implements geometry calculations for glyph analysis.
"""

import numpy
from scipy.spatial import ConvexHull
from typing import Dict


def compute_convex_hull(points: numpy.ndarray) -> Dict:
	"""
	Compute convex hull of point set.

	Args:
		points: Nx2 array of (x,y) coordinates

	Returns:
		Dict with:
		- vertices: Mx2 array of hull vertices
		- area: hull area in square pixels
		- perimeter: hull perimeter in pixels
	"""
	if len(points) < 3:
		raise ValueError("Need at least 3 points to compute convex hull")

	hull = ConvexHull(points)

	# Extract hull vertices
	hull_vertices = points[hull.vertices]

	# Compute perimeter
	perimeter = 0.0
	for i in range(len(hull_vertices)):
		p1 = hull_vertices[i]
		p2 = hull_vertices[(i + 1) % len(hull_vertices)]
		perimeter += numpy.linalg.norm(p2 - p1)

	return {
		'vertices': hull_vertices,
		'area': hull.volume,  # In 2D, volume attribute is area
		'perimeter': perimeter
	}


def fit_axis_aligned_ellipse(points: numpy.ndarray) -> Dict:
	"""
	Fit axis-aligned ellipse (vertical major axis, horizontal minor axis).

	Args:
		points: Nx2 array of (x,y) coordinates

	Returns:
		Dict with:
		- center: (cx, cy) pixel coordinates
		- major_axis: vertical semi-axis length (a)
		- minor_axis: horizontal semi-axis length (b)
		- area: pi * a * b
		- eccentricity: sqrt(1 - (b/a)^2)
	"""
	if len(points) < 2:
		raise ValueError("Need at least 2 points to fit ellipse")

	# Compute center as mean of points
	center_x = numpy.mean(points[:, 0])
	center_y = numpy.mean(points[:, 1])
	center = numpy.array([center_x, center_y])

	# Project points to centered coordinates
	centered_points = points - center

	# Compute standard deviations along x and y axes
	# For points uniformly distributed on an ellipse:
	# std = semi_axis / sqrt(2)
	# Therefore: semi_axis = std * sqrt(2)
	std_x = numpy.std(centered_points[:, 0])
	std_y = numpy.std(centered_points[:, 1])

	# Minor axis is horizontal (x-direction), major axis is vertical (y-direction)
	# Use sqrt(2) * std for semi-axis length
	minor_axis = numpy.sqrt(2.0) * std_x
	major_axis = numpy.sqrt(2.0) * std_y

	# Ensure major >= minor (major axis should be vertical)
	# If not, swap them
	if minor_axis > major_axis:
		minor_axis, major_axis = major_axis, minor_axis

	# Compute area
	area = numpy.pi * major_axis * minor_axis

	# Compute eccentricity
	# e = sqrt(1 - (b/a)^2) where a is major, b is minor
	if major_axis > 0:
		eccentricity = numpy.sqrt(1.0 - (minor_axis / major_axis) ** 2)
	else:
		eccentricity = 0.0

	return {
		'center': center.tolist(),
		'major_axis': float(major_axis),
		'minor_axis': float(minor_axis),
		'area': float(area),
		'eccentricity': float(eccentricity)
	}


def compute_fit_quality(points: numpy.ndarray, ellipse: Dict) -> Dict:
	"""
	Measure quality of ellipse fit.

	Args:
		points: Nx2 array of (x,y) coordinates
		ellipse: Ellipse parameters dict from fit_axis_aligned_ellipse

	Returns:
		Dict with:
		- rmse: root mean squared distance to ellipse
		- max_error: maximum point-to-ellipse distance
		- coverage: fraction of points inside ellipse
	"""
	center = numpy.array(ellipse['center'])
	a = ellipse['major_axis']  # vertical (y)
	b = ellipse['minor_axis']  # horizontal (x)

	# Center points
	centered = points - center

	# For axis-aligned ellipse: (x/b)^2 + (y/a)^2 = 1
	# Points inside have value < 1, outside have value > 1
	x = centered[:, 0]
	y = centered[:, 1]

	if a == 0 or b == 0:
		# Degenerate ellipse
		return {
			'rmse': float('inf'),
			'max_error': float('inf'),
			'coverage': 0.0
		}

	# Compute ellipse equation value for each point
	ellipse_values = (x / b) ** 2 + (y / a) ** 2

	# Distance to ellipse boundary (approximate)
	# For points on boundary, ellipse_value = 1
	# Distance is proportional to |ellipse_value - 1|
	# Scale by average radius for meaningful distance
	avg_radius = (a + b) / 2
	distances = numpy.abs(ellipse_values - 1.0) * avg_radius

	# Compute metrics
	rmse = numpy.sqrt(numpy.mean(distances ** 2))
	max_error = numpy.max(distances)
	coverage = numpy.sum(ellipse_values <= 1.0) / len(points)

	return {
		'rmse': float(rmse),
		'max_error': float(max_error),
		'coverage': float(coverage)
	}
