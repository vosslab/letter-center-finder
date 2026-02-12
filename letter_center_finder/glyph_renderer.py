"""
Render isolated glyphs from SVG using per-character color isolation.

For each target character, builds a temporary SVG where only that character
is visible (everything else is white). Renders via rsvg-convert for accurate
font and position fidelity. Extracts binary mask and contour from the render.
"""

import os
import copy
import tempfile
import subprocess

import numpy
import cv2
import xml.etree.ElementTree as ET

# SVG namespace used in target files
SVG_NS = "http://www.w3.org/2000/svg"
WHITE = "#ffffff"

# Style attributes that must propagate to all tspan fragments
_STYLE_ATTRS = ('font-size', 'font-weight', 'font-family', 'font-style')
# Position attributes that go only on the first tspan fragment
_POS_ATTRS = ('dx', 'dy')


#============================================
def render_isolated_glyph(svg_path: str, char_meta: dict, zoom: int = 10) -> numpy.ndarray:
	"""
	Render a single character from the SVG in isolation.

	Creates a temp SVG where only the target character is visible,
	renders it with rsvg-convert, and returns the grayscale image.

	Args:
		svg_path: Path to original SVG file
		char_meta: Character metadata dict from svg_parser (must include
			_text_elem_index, _tspan_index, _char_offset, fill_color)
		zoom: Render zoom factor (default 10 for high resolution)

	Returns:
		Grayscale numpy array (uint8) of the rendered image
	"""
	# Build the isolation SVG content
	isolation_svg = _build_isolation_svg(svg_path, char_meta)

	# Render to PNG via rsvg-convert
	image = _render_svg_string(isolation_svg, zoom)

	return image


#============================================
def _build_isolation_svg(svg_path: str, char_meta: dict) -> str:
	"""
	Build an SVG string where only the target character is visible.

	All paths, polygons, lines are removed. All text elements are removed
	except the one containing the target character, which is restructured
	so only the target character has its original fill color.

	Args:
		svg_path: Path to original SVG
		char_meta: Character metadata with element identification fields

	Returns:
		SVG content as a string
	"""
	tree = ET.parse(svg_path)  # nosec B314 - local SVG files only
	root = tree.getroot()

	# Register default namespace so output has clean tags
	ET.register_namespace('', SVG_NS)

	# Create new SVG root with same dimensions
	new_root = ET.Element(f'{{{SVG_NS}}}svg')
	new_root.set('version', '1.1')
	for attr in ('width', 'height', 'viewBox', 'preserveAspectRatio'):
		val = root.get(attr)
		if val is not None:
			new_root.set(attr, val)

	# Add white background covering the full viewBox
	vb_str = root.get('viewBox', '')
	if vb_str:
		parts = vb_str.split()
		vb_x, vb_y = float(parts[0]), float(parts[1])
		vb_w, vb_h = float(parts[2]), float(parts[3])
	else:
		vb_x, vb_y = 0.0, 0.0
		vb_w = float(root.get('width', '300').replace('px', ''))
		vb_h = float(root.get('height', '300').replace('px', ''))

	# Background rect with generous padding
	bg = ET.SubElement(new_root, f'{{{SVG_NS}}}rect')
	bg.set('x', str(vb_x - 50))
	bg.set('y', str(vb_y - 50))
	bg.set('width', str(vb_w + 100))
	bg.set('height', str(vb_h + 100))
	bg.set('fill', WHITE)

	# Find the target text element in the original SVG
	text_tag = f'{{{SVG_NS}}}text'
	text_elements = root.findall(f'.//{text_tag}')
	text_idx = char_meta['_text_elem_index']
	target_text = text_elements[text_idx]

	# Deep copy and modify the text element
	text_copy = copy.deepcopy(target_text)
	_isolate_character(text_copy, char_meta)

	new_root.append(text_copy)

	# Write to string
	svg_string = ET.tostring(new_root, encoding='unicode', xml_declaration=True)
	return svg_string


#============================================
def _isolate_character(text_elem, char_meta: dict) -> None:
	"""
	Modify a text element in-place so only the target character is visible.

	Sets the text element fill to white, then restores color only on the
	target character via tspan manipulation.

	Args:
		text_elem: Deep-copied text XML element to modify
		char_meta: Character metadata with _tspan_index, _char_offset, fill_color
	"""
	tspan_idx = char_meta.get('_tspan_index')
	char_offset = char_meta['_char_offset']
	original_fill = char_meta['fill_color']

	tspan_tag = f'{{{SVG_NS}}}tspan'
	tspan_children = [child for child in text_elem if child.tag == tspan_tag]

	if tspan_idx is None:
		# Target character is in direct text of the text element
		_isolate_in_direct_text(text_elem, char_offset, original_fill, tspan_tag)
		# White out any tspan children
		for tspan in tspan_children:
			tspan.set('fill', WHITE)
	else:
		# Target character is in a tspan child
		# White out the direct text via parent fill
		text_elem.set('fill', WHITE)
		# Process each tspan
		for i, tspan in enumerate(tspan_children):
			if i != tspan_idx:
				# White out non-target tspans
				tspan.set('fill', WHITE)
			else:
				# Isolate character in this tspan
				tspan_text = tspan.text or ''
				if len(tspan_text) <= 1:
					# Single char tspan, just set fill
					tspan.set('fill', original_fill)
				else:
					# Multi-char tspan needs splitting
					_split_tspan_for_isolation(
						text_elem, tspan, char_offset, original_fill, tspan_tag
					)


#============================================
def _isolate_in_direct_text(text_elem, char_offset: int, fill: str, tspan_tag: str) -> None:
	"""
	Isolate a character from the text element's direct text content.

	Replaces direct text with tspan fragments: white-filled parts before and
	after, and the target character with the original fill.

	Args:
		text_elem: Text XML element
		char_offset: Character index within the direct text
		fill: Original fill color for the target character
		tspan_tag: Namespace-qualified tspan tag name
	"""
	direct_text = text_elem.text or ''
	# Clear direct text, will be replaced by tspans
	text_elem.text = None
	# Set base fill to white so any inherited fills are white
	text_elem.set('fill', WHITE)

	before = direct_text[:char_offset]
	target_char = direct_text[char_offset]
	after = direct_text[char_offset + 1:]

	# Collect existing children to re-append after our new tspans
	existing_children = list(text_elem)
	for child in existing_children:
		text_elem.remove(child)

	# Insert tspan fragments for the direct text
	if before:
		ts = ET.SubElement(text_elem, tspan_tag)
		ts.text = before
		ts.set('fill', WHITE)

	ts = ET.SubElement(text_elem, tspan_tag)
	ts.text = target_char
	ts.set('fill', fill)

	if after:
		ts = ET.SubElement(text_elem, tspan_tag)
		ts.text = after
		ts.set('fill', WHITE)

	# Re-append existing children (tspans) with white fill
	for child in existing_children:
		child.set('fill', WHITE)
		text_elem.append(child)


#============================================
def _split_tspan_for_isolation(
	text_elem, tspan, char_offset: int, fill: str, tspan_tag: str
) -> None:
	"""
	Split a multi-character tspan to isolate one character.

	Replaces the original tspan with 2-3 tspan fragments. Style attributes
	(font-size etc.) propagate to all fragments. Position attributes (dx, dy)
	go only on the first fragment.

	Args:
		text_elem: Parent text element
		tspan: The tspan to split
		char_offset: Index of the target character within the tspan text
		fill: Original fill color for the target character
		tspan_tag: Namespace-qualified tspan tag name
	"""
	tspan_text = tspan.text or ''
	before = tspan_text[:char_offset]
	target_char = tspan_text[char_offset]
	after = tspan_text[char_offset + 1:]

	# Collect style attributes to propagate to all fragments
	style_attrs = {}
	for attr in _STYLE_ATTRS:
		val = tspan.get(attr)
		if val is not None:
			style_attrs[attr] = val

	# Position attributes go only on the first fragment
	pos_attrs = {}
	for attr in _POS_ATTRS:
		val = tspan.get(attr)
		if val is not None:
			pos_attrs[attr] = val

	# Find index of this tspan in the parent element
	children = list(text_elem)
	idx = children.index(tspan)

	# Preserve tail text (text between this tspan and the next sibling)
	tail = tspan.tail

	# Remove the original tspan
	text_elem.remove(tspan)

	# Build replacement fragments
	replacements = []
	is_first = True

	if before:
		ts = ET.Element(tspan_tag)
		ts.text = before
		ts.set('fill', WHITE)
		for k, v in style_attrs.items():
			ts.set(k, v)
		if is_first:
			for k, v in pos_attrs.items():
				ts.set(k, v)
			is_first = False
		replacements.append(ts)

	# Target character fragment
	ts = ET.Element(tspan_tag)
	ts.text = target_char
	ts.set('fill', fill)
	for k, v in style_attrs.items():
		ts.set(k, v)
	if is_first:
		for k, v in pos_attrs.items():
			ts.set(k, v)
		is_first = False
	replacements.append(ts)

	if after:
		ts = ET.Element(tspan_tag)
		ts.text = after
		ts.set('fill', WHITE)
		for k, v in style_attrs.items():
			ts.set(k, v)
		# No position attrs on non-first fragments
		replacements.append(ts)

	# Assign tail text to the last replacement fragment
	if tail and replacements:
		replacements[-1].tail = tail

	# Insert replacements at the original position
	for i, ts in enumerate(replacements):
		text_elem.insert(idx + i, ts)


#============================================
def _render_svg_string(svg_string: str, zoom: int = 10) -> numpy.ndarray:
	"""
	Render an SVG string to a grayscale numpy array via rsvg-convert.

	Args:
		svg_string: SVG content as a string
		zoom: Zoom factor for rsvg-convert

	Returns:
		Grayscale numpy array (uint8)
	"""
	# Write SVG to temp file, render to PNG, read PNG
	with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as svg_f:
		svg_f.write(svg_string)
		svg_tmp = svg_f.name

	png_tmp = svg_tmp.replace('.svg', '.png')

	try:
		# Render with rsvg-convert
		cmd = [
			'rsvg-convert',
			f'--zoom={zoom}',
			'-o', png_tmp,
			svg_tmp,
		]
		result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
		if result.returncode != 0:
			raise RuntimeError(f"rsvg-convert failed: {result.stderr}")

		# Read the PNG as grayscale
		image = cv2.imread(png_tmp, cv2.IMREAD_GRAYSCALE)
		if image is None:
			raise RuntimeError(f"Failed to read rendered PNG: {png_tmp}")
		return image

	finally:
		# Clean up temp files
		if os.path.exists(svg_tmp):
			os.unlink(svg_tmp)
		if os.path.exists(png_tmp):
			os.unlink(png_tmp)


#============================================
def extract_binary_mask(glyph_image: numpy.ndarray) -> numpy.ndarray:
	"""
	Convert grayscale rendered image to binary mask of the glyph.

	Uses Otsu's thresholding. The isolation SVG ensures the glyph is the
	only non-white content in the image.

	Args:
		glyph_image: Grayscale image from render_isolated_glyph()

	Returns:
		Binary image: 255 = glyph pixels, 0 = background
	"""
	# Invert: black text on white bg -> white glyph on black bg
	_, binary = cv2.threshold(
		glyph_image, 0, 255,
		cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
	)

	# Morphological closing to fill small anti-aliasing gaps
	kernel = numpy.ones((3, 3), numpy.uint8)
	binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

	return binary


#============================================
def extract_contour_points(binary_mask: numpy.ndarray) -> numpy.ndarray:
	"""
	Extract outer contour points from binary glyph mask.

	Since the isolation SVG contains only one character, the largest
	contour is the glyph outline.

	Args:
		binary_mask: Binary image (255 = glyph, 0 = background)

	Returns:
		Nx2 array of (x, y) pixel coordinates
	"""
	contours, _ = cv2.findContours(
		binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
	)

	if len(contours) == 0:
		raise ValueError("No contours found in binary mask")

	# Select largest contour (the glyph)
	largest_contour = max(contours, key=cv2.contourArea)

	# Reshape from Nx1x2 to Nx2
	points = largest_contour.reshape(-1, 2)
	return points
