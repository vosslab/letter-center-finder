"""
Unit tests for glyph_renderer module.
"""

import numpy
import pytest
from letter_center_finder import glyph_renderer


def test_render_single_glyph_O():
	"""Test rendering the letter O."""
	glyph = glyph_renderer.render_single_glyph('O', 12.0)

	assert isinstance(glyph, numpy.ndarray)
	assert glyph.dtype == numpy.uint8
	assert len(glyph.shape) == 2  # 2D grayscale image
	assert glyph.shape[0] > 0 and glyph.shape[1] > 0


def test_render_single_glyph_C():
	"""Test rendering the letter C."""
	glyph = glyph_renderer.render_single_glyph('C', 12.0)

	assert isinstance(glyph, numpy.ndarray)
	assert glyph.dtype == numpy.uint8
	assert len(glyph.shape) == 2
	assert glyph.shape[0] > 0 and glyph.shape[1] > 0


def test_render_with_scale_factor():
	"""Test rendering with different scale factors."""
	glyph_1x = glyph_renderer.render_single_glyph('O', 12.0, scale_factor=1)
	glyph_4x = glyph_renderer.render_single_glyph('O', 12.0, scale_factor=4)

	# Higher scale factor should produce larger image
	assert glyph_4x.shape[0] > glyph_1x.shape[0]
	assert glyph_4x.shape[1] > glyph_1x.shape[1]


def test_extract_binary_mask():
	"""Test converting glyph to binary mask."""
	glyph = glyph_renderer.render_single_glyph('O', 12.0)
	binary = glyph_renderer.extract_binary_mask(glyph)

	assert isinstance(binary, numpy.ndarray)
	assert binary.dtype == numpy.uint8
	assert binary.shape == glyph.shape

	# Binary mask should only have values 0 and 255
	unique_values = numpy.unique(binary)
	assert all(val in [0, 255] for val in unique_values)

	# Should have some foreground pixels (the glyph)
	assert numpy.sum(binary == 255) > 0


def test_extract_contour_points():
	"""Test extracting contour points from binary mask."""
	glyph = glyph_renderer.render_single_glyph('O', 12.0)
	binary = glyph_renderer.extract_binary_mask(glyph)
	contour = glyph_renderer.extract_contour_points(binary)

	assert isinstance(contour, numpy.ndarray)
	assert len(contour.shape) == 2
	assert contour.shape[1] == 2  # Nx2 array

	# Should have a reasonable number of contour points
	assert len(contour) > 10


def test_extract_contour_empty_mask():
	"""Test that extracting contour from empty mask raises error."""
	empty_mask = numpy.zeros((50, 50), dtype=numpy.uint8)

	with pytest.raises(ValueError, match="No contours found"):
		glyph_renderer.extract_contour_points(empty_mask)


def test_crop_to_content():
	"""Test cropping image to content."""
	# Create image with white background and small black square
	image = numpy.ones((100, 100), dtype=numpy.uint8) * 255
	image[40:60, 40:60] = 0

	cropped = glyph_renderer._crop_to_content(image, padding=5)

	# Cropped image should be smaller
	assert cropped.shape[0] < image.shape[0]
	assert cropped.shape[1] < image.shape[1]

	# Should include the black square with padding (approximately)
	# Allow for off-by-one due to pixel boundaries
	assert cropped.shape[0] >= 20 + 2 * 5 - 1  # square size + padding
	assert cropped.shape[1] >= 20 + 2 * 5 - 1
