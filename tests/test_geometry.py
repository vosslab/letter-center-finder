"""
Unit tests for geometry module.
"""

import numpy
import pytest
from letter_center_finder import geometry


def test_compute_convex_hull_square():
	"""Test convex hull on a square."""
	# Create square points
	points = numpy.array([
		[0, 0], [10, 0], [10, 10], [0, 10],
		[5, 5], [3, 3], [7, 7]  # Interior points
	])

	hull = geometry.compute_convex_hull(points)

	assert 'vertices' in hull
	assert 'area' in hull
	assert 'perimeter' in hull

	# Hull should have 4 vertices (the corners)
	assert len(hull['vertices']) == 4

	# Area should be 100
	assert abs(hull['area'] - 100.0) < 1.0

	# Perimeter should be 40
	assert abs(hull['perimeter'] - 40.0) < 1.0


def test_compute_convex_hull_triangle():
	"""Test convex hull on a triangle."""
	points = numpy.array([
		[0, 0], [10, 0], [5, 10],
		[5, 2], [5, 5], [3, 3]  # Interior points
	])

	hull = geometry.compute_convex_hull(points)

	# Triangle should have 3 vertices
	assert len(hull['vertices']) == 3

	# Area should be 50 (base * height / 2 = 10 * 10 / 2)
	assert abs(hull['area'] - 50.0) < 1.0


def test_convex_hull_too_few_points():
	"""Test that convex hull raises error with too few points."""
	points = numpy.array([[0, 0], [1, 1]])

	with pytest.raises(ValueError):
		geometry.compute_convex_hull(points)


def test_fit_axis_aligned_ellipse_circle():
	"""Test ellipse fit on circular points."""
	# Generate points on a circle
	t = numpy.linspace(0, 2 * numpy.pi, 100, endpoint=False)
	radius = 10.0
	center_x, center_y = 50.0, 50.0
	points = numpy.column_stack([
		center_x + radius * numpy.cos(t),
		center_y + radius * numpy.sin(t)
	])

	ellipse = geometry.fit_axis_aligned_ellipse(points)

	assert 'center' in ellipse
	assert 'major_axis' in ellipse
	assert 'minor_axis' in ellipse
	assert 'area' in ellipse
	assert 'eccentricity' in ellipse

	# Center should be near (50, 50)
	assert abs(ellipse['center'][0] - center_x) < 1.0
	assert abs(ellipse['center'][1] - center_y) < 1.0

	# For circle, major and minor axes should be similar
	assert abs(ellipse['major_axis'] - ellipse['minor_axis']) < 2.0

	# Eccentricity of circle should be near 0
	assert ellipse['eccentricity'] < 0.2


def test_fit_axis_aligned_ellipse_vertical():
	"""Test ellipse fit on vertically-oriented ellipse."""
	# Generate points on vertical ellipse (taller than wide)
	t = numpy.linspace(0, 2 * numpy.pi, 100, endpoint=False)
	a = 20.0  # vertical semi-axis
	b = 10.0  # horizontal semi-axis
	center_x, center_y = 50.0, 50.0
	points = numpy.column_stack([
		center_x + b * numpy.cos(t),
		center_y + a * numpy.sin(t)
	])

	ellipse = geometry.fit_axis_aligned_ellipse(points)

	# Major axis should be greater than minor axis
	assert ellipse['major_axis'] > ellipse['minor_axis']

	# Major axis (semi-axis) should be roughly a = 20
	assert abs(ellipse['major_axis'] - a) < 2.0

	# Minor axis (semi-axis) should be roughly b = 10
	assert abs(ellipse['minor_axis'] - b) < 2.0

	# Eccentricity should be significant (not a circle)
	assert ellipse['eccentricity'] > 0.5


def test_fit_ellipse_too_few_points():
	"""Test that ellipse fit raises error with too few points."""
	points = numpy.array([[0, 0]])

	with pytest.raises(ValueError):
		geometry.fit_axis_aligned_ellipse(points)


def test_compute_fit_quality():
	"""Test fit quality metrics."""
	# Generate perfect circular points
	t = numpy.linspace(0, 2 * numpy.pi, 100, endpoint=False)
	radius = 10.0
	points = numpy.column_stack([
		radius * numpy.cos(t),
		radius * numpy.sin(t)
	])

	ellipse = geometry.fit_axis_aligned_ellipse(points)
	quality = geometry.compute_fit_quality(points, ellipse)

	assert 'rmse' in quality
	assert 'max_error' in quality
	assert 'coverage' in quality

	# For perfect fit, RMSE should be small
	assert quality['rmse'] < 5.0

	# Most points should be inside ellipse
	assert quality['coverage'] > 0.8
	assert quality['coverage'] <= 1.0


def test_fit_quality_degenerate_ellipse():
	"""Test fit quality with degenerate ellipse."""
	points = numpy.array([[0, 0], [1, 1]])

	# Create degenerate ellipse
	ellipse = {
		'center': [0.5, 0.5],
		'major_axis': 0.0,
		'minor_axis': 0.0,
		'area': 0.0,
		'eccentricity': 0.0
	}

	quality = geometry.compute_fit_quality(points, ellipse)

	# Degenerate ellipse should have infinite RMSE
	assert quality['rmse'] == float('inf')
	assert quality['max_error'] == float('inf')
	assert quality['coverage'] == 0.0
