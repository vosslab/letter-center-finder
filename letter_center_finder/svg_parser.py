"""
Parse SVG files to extract O and C character metadata.

Extracts position, font attributes, and text content for individual characters.
Font metric constants ported from bkchem/tools/measure_glyph_bond_alignment.py.
Also provides viewBox extraction and SVG-to-pixel coordinate mapping.
"""

import xml.etree.ElementTree as ET

# SVG namespace used in target files
SVG_NS = "http://www.w3.org/2000/svg"


#============================================
def _glyph_char_advance(font_size: float, char: str) -> float:
	"""Estimated horizontal advance for one character."""
	size = max(1.0, float(font_size))
	upper = char.upper()
	if upper in ('I', 'L', '1'):
		return size * 0.38
	if upper in ('W', 'M'):
		return size * 0.82
	if upper in ('O', 'C', 'S', 'Q', 'G', 'D', 'U', '0', '6', '9', '8'):
		return size * 0.62
	if upper in ('H', 'N', 'P', 'T', 'F', 'K', 'E', 'X', 'Y'):
		return size * 0.58
	if char.isdigit():
		return size * 0.52
	if char.islower():
		return size * 0.50
	return size * 0.56  # default


#============================================
def _glyph_char_vertical_bounds(baseline_y: float, font_size: float, char: str) -> tuple:
	"""Return (top_y, bottom_y) for a character at baseline_y."""
	size = max(1.0, float(font_size))
	upper = char.upper()
	if upper in ('C', 'O', 'S', 'Q', 'G', 'D'):
		return (baseline_y - size * 0.78, baseline_y + size * 0.16)
	return (baseline_y - size * 0.80, baseline_y + size * 0.20)


#============================================
def _glyph_text_width(text: str, font_size: float) -> float:
	"""Total text width from per-character advances."""
	advances = [_glyph_char_advance(font_size, c) for c in text]
	tracking = max(0.0, font_size) * 0.04
	return sum(advances) + tracking * max(0, len(advances) - 1)


#============================================
def get_svg_dimensions(svg_path: str) -> dict:
	"""
	Extract viewBox and viewport dimensions from SVG file.

	Args:
		svg_path: Path to SVG file

	Returns:
		Dict with viewBox (x, y, width, height), viewport_width, viewport_height
	"""
	tree = ET.parse(svg_path)  # nosec B314 - local SVG files only
	root = tree.getroot()
	return _get_dimensions_from_root(root)


#============================================
def _get_dimensions_from_root(root) -> dict:
	"""
	Extract viewBox and viewport dimensions from SVG root element.

	Args:
		root: XML root element of SVG

	Returns:
		Dict with viewBox dict and viewport dimensions
	"""
	viewbox_str = root.get('viewBox', '')
	# Strip units from width/height (e.g. "260px" -> "260")
	width_str = root.get('width', '300').replace('px', '').strip()
	height_str = root.get('height', '300').replace('px', '').strip()
	width = float(width_str)
	height = float(height_str)

	if viewbox_str:
		parts = viewbox_str.split()
		vb = {
			'x': float(parts[0]),
			'y': float(parts[1]),
			'width': float(parts[2]),
			'height': float(parts[3]),
		}
	else:
		vb = {'x': 0.0, 'y': 0.0, 'width': width, 'height': height}

	return {
		'viewBox': vb,
		'viewport_width': width,
		'viewport_height': height,
	}


#============================================
def svg_to_pixel(svg_x: float, svg_y: float, svg_dims: dict, zoom: float = 1.0) -> tuple:
	"""
	Convert SVG coordinates to pixel coordinates.

	Assumes preserveAspectRatio="xMidYMid meet" (the SVG default).

	Args:
		svg_x: X coordinate in SVG user units
		svg_y: Y coordinate in SVG user units
		svg_dims: Dict from get_svg_dimensions()
		zoom: Render zoom factor (default 1.0)

	Returns:
		Tuple (pixel_x, pixel_y)
	"""
	vb = svg_dims['viewBox']
	vp_w = svg_dims['viewport_width'] * zoom
	vp_h = svg_dims['viewport_height'] * zoom

	# Scale to fit (meet = use smaller scale)
	scale = min(vp_w / vb['width'], vp_h / vb['height'])
	rendered_w = vb['width'] * scale
	rendered_h = vb['height'] * scale
	# Center in viewport (xMid, YMid)
	offset_x = (vp_w - rendered_w) / 2.0
	offset_y = (vp_h - rendered_h) / 2.0

	px = (svg_x - vb['x']) * scale + offset_x
	py = (svg_y - vb['y']) * scale + offset_y
	return (px, py)


#============================================
def pixel_to_svg(pixel_x: float, pixel_y: float, svg_dims: dict, zoom: float = 1.0) -> tuple:
	"""
	Convert pixel coordinates to SVG coordinates.

	Inverse of svg_to_pixel(). Assumes preserveAspectRatio="xMidYMid meet".

	Args:
		pixel_x: X pixel coordinate
		pixel_y: Y pixel coordinate
		svg_dims: Dict from get_svg_dimensions()
		zoom: Render zoom factor (default 1.0)

	Returns:
		Tuple (svg_x, svg_y)
	"""
	vb = svg_dims['viewBox']
	vp_w = svg_dims['viewport_width'] * zoom
	vp_h = svg_dims['viewport_height'] * zoom

	scale = min(vp_w / vb['width'], vp_h / vb['height'])
	rendered_w = vb['width'] * scale
	rendered_h = vb['height'] * scale
	offset_x = (vp_w - rendered_w) / 2.0
	offset_y = (vp_h - rendered_h) / 2.0

	sx = (pixel_x - offset_x) / scale + vb['x']
	sy = (pixel_y - offset_y) / scale + vb['y']
	return (sx, sy)


#============================================
def parse_svg_file(svg_path: str) -> list:
	"""
	Parse SVG and extract all O and C characters with their metadata.

	Each character dict includes element identification fields needed
	by the isolation SVG builder:
	- _text_elem_index: index of the <text> element in document order
	- _tspan_index: index of the <tspan> within the text element, or None
	- _char_offset: character offset within the text/tspan string

	Args:
		svg_path: Path to SVG file

	Returns:
		List of character metadata dicts
	"""
	tree = ET.parse(svg_path)  # nosec B314 - local SVG files only
	root = tree.getroot()

	# SVG namespace
	ns = {'svg': SVG_NS}

	characters = []

	# Find all text elements and track their index
	text_elements = root.findall(f'.//{{{SVG_NS}}}text')
	for text_idx, text_elem in enumerate(text_elements):
		chars_in_element = _extract_characters_from_text_element(
			text_elem, ns, text_idx
		)
		characters.extend(chars_in_element)

	return characters


#============================================
def _extract_characters_from_text_element(elem, ns: dict, text_elem_index: int) -> list:
	"""
	Extract O/C characters from text element including tspans.

	Args:
		elem: XML element (text element)
		ns: Namespace dict
		text_elem_index: Index of this text element among all text elements

	Returns:
		List of character metadata dicts for each O or C found
	"""
	characters = []

	# Get default attributes from text element
	base_x = float(elem.get('x', '0'))
	base_y = float(elem.get('y', '0'))
	base_font_family = elem.get('font-family', 'sans-serif')
	base_font_size = float(elem.get('font-size', '12'))
	base_font_weight = elem.get('font-weight', 'normal')
	base_fill = elem.get('fill', '#000000')
	base_text_anchor = elem.get('text-anchor', 'start')

	# Get style attributes if present
	style = elem.get('style', '')
	if style:
		style_dict = _parse_style_attribute(style)
		base_font_family = style_dict.get('font-family', base_font_family)
		base_font_size = float(style_dict.get('font-size', str(base_font_size)).replace('px', ''))
		base_font_weight = style_dict.get('font-weight', base_font_weight)
		base_fill = style_dict.get('fill', base_fill)
		base_text_anchor = style_dict.get('text-anchor', base_text_anchor)

	# Get full source text for debugging
	source_text = ET.tostring(elem, encoding='unicode', method='text').strip()

	# Check direct text content (no tspan)
	direct_text = elem.text or ''
	characters.extend(_extract_chars_from_string(
		direct_text, base_x, base_y, base_text_anchor, base_font_family,
		base_font_size, base_font_weight, base_fill, source_text,
		text_elem_index=text_elem_index,
		tspan_index=None,
	))

	# Check tspan elements
	tspan_tag = f'{{{SVG_NS}}}tspan'
	tspan_children = [child for child in elem if child.tag == tspan_tag]
	for tspan_idx, tspan in enumerate(tspan_children):
		# Get tspan-specific attributes (or inherit from parent)
		tspan_x = float(tspan.get('x', str(base_x)))
		tspan_y = float(tspan.get('y', str(base_y)))
		tspan_font_family = tspan.get('font-family', base_font_family)
		tspan_font_size = float(tspan.get('font-size', str(base_font_size)))
		tspan_font_weight = tspan.get('font-weight', base_font_weight)
		tspan_fill = tspan.get('fill', base_fill)
		tspan_text_anchor = tspan.get('text-anchor', base_text_anchor)

		# Check tspan style
		tspan_style = tspan.get('style', '')
		if tspan_style:
			style_dict = _parse_style_attribute(tspan_style)
			tspan_font_family = style_dict.get('font-family', tspan_font_family)
			tspan_font_size = float(style_dict.get('font-size', str(tspan_font_size)).replace('px', ''))
			tspan_font_weight = style_dict.get('font-weight', tspan_font_weight)
			tspan_fill = style_dict.get('fill', tspan_fill)
			tspan_text_anchor = style_dict.get('text-anchor', tspan_text_anchor)

		tspan_text = tspan.text or ''
		characters.extend(_extract_chars_from_string(
			tspan_text, tspan_x, tspan_y, tspan_text_anchor, tspan_font_family,
			tspan_font_size, tspan_font_weight, tspan_fill, source_text,
			text_elem_index=text_elem_index,
			tspan_index=tspan_idx,
		))

	return characters


#============================================
def _parse_style_attribute(style: str) -> dict:
	"""
	Parse CSS style attribute into dict.

	Args:
		style: CSS style string (e.g., "font-size:12px;fill:#000")

	Returns:
		Dict of style properties
	"""
	style_dict = {}
	for item in style.split(';'):
		item = item.strip()
		if ':' in item:
			key, value = item.split(':', 1)
			style_dict[key.strip()] = value.strip()
	return style_dict


#============================================
def _extract_chars_from_string(
	text: str,
	x: float,
	y: float,
	text_anchor: str,
	font_family: str,
	font_size: float,
	font_weight: str,
	fill: str,
	source_text: str,
	text_elem_index: int = 0,
	tspan_index: int = None,
) -> list:
	"""
	Extract O and C characters from a text string with proper positioning.

	Uses font metrics to compute per-character center coordinates,
	accounting for text-anchor alignment. Also records element identification
	fields needed by the isolation SVG builder.

	Args:
		text: Text to search
		x, y: Position (interpreted per text_anchor)
		text_anchor: 'start', 'middle', or 'end'
		font_family: Font family name
		font_size: Font size
		font_weight: Font weight
		fill: Fill color
		source_text: Original source text for debugging
		text_elem_index: Index of parent text element in SVG
		tspan_index: Index of parent tspan, or None for direct text

	Returns:
		List of character metadata dicts
	"""
	characters = []

	if not text:
		return characters

	# Compute cursor_x based on text_anchor
	text_width = _glyph_text_width(text, font_size)
	tracking = max(0.0, font_size) * 0.04

	if text_anchor == 'middle':
		cursor_x = x - text_width * 0.5
	elif text_anchor == 'end':
		cursor_x = x - text_width
	else:  # 'start'
		cursor_x = x

	# Walk through characters, accumulating advance widths
	for i, char in enumerate(text):
		advance = _glyph_char_advance(font_size, char)

		if char in ('O', 'C'):
			# Character center x = left edge + half advance
			char_cx = cursor_x + advance * 0.5
			# Character center y from vertical bounds
			top_y, bottom_y = _glyph_char_vertical_bounds(y, font_size, char)
			char_cy = (top_y + bottom_y) * 0.5

			characters.append({
				'character': char,
				'x': cursor_x,
				'y': y,
				'cx': char_cx,
				'cy': char_cy,
				'font_family': font_family,
				'font_size': font_size,
				'font_weight': font_weight,
				'fill_color': fill,
				'source_text': source_text,
				'char_index': i,
				# Element identification for isolation SVG builder
				'_text_elem_index': text_elem_index,
				'_tspan_index': tspan_index,
				'_char_offset': i,
			})

		# Advance cursor: char advance + tracking (except after last char)
		if i < len(text) - 1:
			cursor_x += advance + tracking
		else:
			cursor_x += advance

	return characters


# Keep old name as alias for backward compatibility in tests
parse_style_attribute = _parse_style_attribute
extract_characters_from_text_element = _extract_characters_from_text_element
