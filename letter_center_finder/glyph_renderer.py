"""
Render individual characters as clean bitmaps for CV processing.

Uses PIL for text rendering and OpenCV for contour extraction.
"""

import numpy
import cv2
from PIL import Image, ImageDraw, ImageFont


def render_single_glyph(
	character: str,
	font_size: float,
	font_family: str = "sans-serif",
	font_weight: str = "normal",
	scale_factor: int = 4
) -> numpy.ndarray:
	"""
	Render a single character to a high-res grayscale image.

	Args:
		character: Single char to render ('O' or 'C')
		font_size: Font size in points
		font_family: Font family name
		font_weight: 'normal' or 'bold'
		scale_factor: Render at Nx resolution for anti-aliasing

	Returns:
		Grayscale numpy array (uint8, 0=background, 255=glyph)
	"""
	# Calculate internal rendering size
	internal_size = int(font_size * scale_factor)

	# Try to load font, fall back to default
	font = _load_font(font_family, font_weight, internal_size)

	# Create a larger canvas to ensure character fits
	canvas_size = internal_size * 3
	image = Image.new('L', (canvas_size, canvas_size), color=255)  # White background
	draw = ImageDraw.Draw(image)

	# Get text bounding box to center it
	bbox = draw.textbbox((0, 0), character, font=font)
	text_width = bbox[2] - bbox[0]
	text_height = bbox[3] - bbox[1]

	# Center the character
	x = (canvas_size - text_width) // 2 - bbox[0]
	y = (canvas_size - text_height) // 2 - bbox[1]

	# Draw black text on white background
	draw.text((x, y), character, fill=0, font=font)

	# Convert to numpy array
	glyph_array = numpy.array(image)

	# Crop to content with some padding
	glyph_array = _crop_to_content(glyph_array, padding=10)

	return glyph_array


def _load_font(font_family: str, font_weight: str, size: int) -> ImageFont.FreeTypeFont:
	"""
	Load font with fallback to default.

	Args:
		font_family: Font family name
		font_weight: Font weight ('normal' or 'bold')
		size: Font size in points

	Returns:
		PIL ImageFont object
	"""
	# Common font paths for macOS
	font_paths = []

	if font_weight == 'bold':
		font_paths = [
			'/System/Library/Fonts/Helvetica.ttc',
			'/System/Library/Fonts/Supplemental/Arial Bold.ttf',
			'/Library/Fonts/Arial Bold.ttf',
		]
	else:
		font_paths = [
			'/System/Library/Fonts/Helvetica.ttc',
			'/System/Library/Fonts/Supplemental/Arial.ttf',
			'/Library/Fonts/Arial.ttf',
		]

	# Try each font path
	for font_path in font_paths:
		try:
			return ImageFont.truetype(font_path, size)
		except (OSError, IOError):
			continue

	# Fall back to default font
	try:
		return ImageFont.load_default()
	except:
		# If even default fails, return None and PIL will use built-in
		return None


def _crop_to_content(image: numpy.ndarray, padding: int = 10) -> numpy.ndarray:
	"""
	Crop image to content bounding box with padding.

	Args:
		image: Grayscale image (white background)
		padding: Pixels to add around content

	Returns:
		Cropped image
	"""
	# Find non-white pixels
	coords = numpy.column_stack(numpy.where(image < 250))

	if len(coords) == 0:
		# No content, return small blank image
		return image[0:50, 0:50]

	# Get bounding box
	y_min, x_min = coords.min(axis=0)
	y_max, x_max = coords.max(axis=0)

	# Add padding
	y_min = max(0, y_min - padding)
	x_min = max(0, x_min - padding)
	y_max = min(image.shape[0], y_max + padding)
	x_max = min(image.shape[1], x_max + padding)

	return image[y_min:y_max, x_min:x_max]


def extract_binary_mask(glyph_image: numpy.ndarray) -> numpy.ndarray:
	"""
	Convert grayscale glyph to binary mask.

	Args:
		glyph_image: Grayscale image (white background, black text)

	Returns:
		Binary image: 255=glyph pixels, 0=background
	"""
	# Use Otsu's method for automatic thresholding
	# THRESH_BINARY_INV because we have black text on white background
	_, binary = cv2.threshold(
		glyph_image,
		0,
		255,
		cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
	)

	# Optional: morphological closing to fill small gaps
	kernel = numpy.ones((3, 3), numpy.uint8)
	binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

	return binary


def extract_contour_points(binary_mask: numpy.ndarray) -> numpy.ndarray:
	"""
	Extract contour points from binary glyph mask.

	Args:
		binary_mask: Binary image (255=glyph, 0=background)

	Returns:
		Nx2 array of (x,y) pixel coordinates
	"""
	# Find contours
	contours, _ = cv2.findContours(
		binary_mask,
		cv2.RETR_EXTERNAL,
		cv2.CHAIN_APPROX_NONE
	)

	if len(contours) == 0:
		raise ValueError("No contours found in binary mask")

	# Select largest contour (should be the glyph)
	largest_contour = max(contours, key=cv2.contourArea)

	# Reshape to Nx2 array
	points = largest_contour.reshape(-1, 2)

	return points
