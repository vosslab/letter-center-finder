"""
Parse SVG files to extract O and C character metadata.

Extracts position, font attributes, and text content for individual characters.
Font metric constants ported from bkchem/tools/measure_glyph_bond_alignment.py.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple


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


def _glyph_char_vertical_bounds(baseline_y: float, font_size: float, char: str) -> Tuple[float, float]:
	"""Return (top_y, bottom_y) for a character at baseline_y."""
	size = max(1.0, float(font_size))
	upper = char.upper()
	if upper in ('C', 'O', 'S', 'Q', 'G', 'D'):
		return (baseline_y - size * 0.78, baseline_y + size * 0.16)
	return (baseline_y - size * 0.80, baseline_y + size * 0.20)


def _glyph_text_width(text: str, font_size: float) -> float:
	"""Total text width from per-character advances."""
	advances = [_glyph_char_advance(font_size, c) for c in text]
	tracking = max(0.0, font_size) * 0.04
	return sum(advances) + tracking * max(0, len(advances) - 1)


def parse_svg_file(svg_path: str) -> List[Dict]:
	"""
	Parse SVG and extract all O and C characters with their metadata.

	Args:
		svg_path: Path to SVG file

	Returns:
		List of dicts containing:
		- character: 'O' or 'C'
		- x, y: position in SVG coordinates
		- cx, cy: estimated glyph center in SVG coordinates
		- font_family: e.g., 'sans-serif'
		- font_size: e.g., 12.0
		- font_weight: 'normal' or 'bold'
		- fill_color: hex color
		- source_text: the full text element content (for debugging)
	"""
	tree = ET.parse(svg_path)  # nosec B314 - local SVG files only
	root = tree.getroot()

	# SVG namespace
	ns = {'svg': 'http://www.w3.org/2000/svg'}

	characters = []

	# Find all text elements
	for text_elem in root.findall('.//svg:text', ns):
		chars_in_element = extract_characters_from_text_element(text_elem, ns)
		characters.extend(chars_in_element)

	return characters


def extract_characters_from_text_element(elem, ns: Dict) -> List[Dict]:
	"""
	Extract O/C characters from text element including tspans.

	Args:
		elem: XML element (text element)
		ns: Namespace dict

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
		style_dict = parse_style_attribute(style)
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
		base_font_size, base_font_weight, base_fill, source_text
	))

	# Check tspan elements
	for tspan in elem.findall('.//svg:tspan', ns):
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
			style_dict = parse_style_attribute(tspan_style)
			tspan_font_family = style_dict.get('font-family', tspan_font_family)
			tspan_font_size = float(style_dict.get('font-size', str(tspan_font_size)).replace('px', ''))
			tspan_font_weight = style_dict.get('font-weight', tspan_font_weight)
			tspan_fill = style_dict.get('fill', tspan_fill)
			tspan_text_anchor = style_dict.get('text-anchor', tspan_text_anchor)

		tspan_text = tspan.text or ''
		characters.extend(_extract_chars_from_string(
			tspan_text, tspan_x, tspan_y, tspan_text_anchor, tspan_font_family,
			tspan_font_size, tspan_font_weight, tspan_fill, source_text
		))

	return characters


def parse_style_attribute(style: str) -> Dict[str, str]:
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


def _extract_chars_from_string(
	text: str,
	x: float,
	y: float,
	text_anchor: str,
	font_family: str,
	font_size: float,
	font_weight: str,
	fill: str,
	source_text: str
) -> List[Dict]:
	"""
	Extract O and C characters from a text string with proper positioning.

	Uses font metrics to compute per-character center coordinates,
	accounting for text-anchor alignment.

	Args:
		text: Text to search
		x, y: Position (interpreted per text_anchor)
		text_anchor: 'start', 'middle', or 'end'
		font_family: Font family name
		font_size: Font size
		font_weight: Font weight
		fill: Fill color
		source_text: Original source text for debugging

	Returns:
		List of character metadata dicts
	"""
	characters = []

	if not text:
		return characters

	# Step 1: Compute cursor_x based on text_anchor
	text_width = _glyph_text_width(text, font_size)
	tracking = max(0.0, font_size) * 0.04

	if text_anchor == 'middle':
		cursor_x = x - text_width * 0.5
	elif text_anchor == 'end':
		cursor_x = x - text_width
	else:  # 'start'
		cursor_x = x

	# Step 2: Walk through characters, accumulating advance widths
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
				'char_index': i
			})

		# Advance cursor: char advance + tracking (except after last char)
		if i < len(text) - 1:
			cursor_x += advance + tracking
		else:
			cursor_x += advance

	return characters
