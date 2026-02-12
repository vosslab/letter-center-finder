"""
Parse SVG files to extract O and C character metadata.

Extracts position, font attributes, and text content for individual characters.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict


def parse_svg_file(svg_path: str) -> List[Dict]:
	"""
	Parse SVG and extract all O and C characters with their metadata.

	Args:
		svg_path: Path to SVG file

	Returns:
		List of dicts containing:
		- character: 'O' or 'C'
		- x, y: position in SVG coordinates
		- font_family: e.g., 'sans-serif'
		- font_size: e.g., 12.0
		- font_weight: 'normal' or 'bold'
		- fill_color: hex color
		- source_text: the full text element content (for debugging)
	"""
	tree = ET.parse(svg_path)
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

	# Get style attributes if present
	style = elem.get('style', '')
	if style:
		style_dict = parse_style_attribute(style)
		base_font_family = style_dict.get('font-family', base_font_family)
		base_font_size = float(style_dict.get('font-size', str(base_font_size)).replace('px', ''))
		base_font_weight = style_dict.get('font-weight', base_font_weight)
		base_fill = style_dict.get('fill', base_fill)

	# Get full source text for debugging
	source_text = ET.tostring(elem, encoding='unicode', method='text').strip()

	# Check direct text content (no tspan)
	direct_text = elem.text or ''
	characters.extend(_extract_chars_from_string(
		direct_text, base_x, base_y, base_font_family,
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

		# Check tspan style
		tspan_style = tspan.get('style', '')
		if tspan_style:
			style_dict = parse_style_attribute(tspan_style)
			tspan_font_family = style_dict.get('font-family', tspan_font_family)
			tspan_font_size = float(style_dict.get('font-size', str(tspan_font_size)).replace('px', ''))
			tspan_font_weight = style_dict.get('font-weight', tspan_font_weight)
			tspan_fill = style_dict.get('fill', tspan_fill)

		tspan_text = tspan.text or ''
		characters.extend(_extract_chars_from_string(
			tspan_text, tspan_x, tspan_y, tspan_font_family,
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
	font_family: str,
	font_size: float,
	font_weight: str,
	fill: str,
	source_text: str
) -> List[Dict]:
	"""
	Extract O and C characters from a text string.

	Args:
		text: Text to search
		x, y: Position
		font_family: Font family name
		font_size: Font size
		font_weight: Font weight
		fill: Fill color
		source_text: Original source text for debugging

	Returns:
		List of character metadata dicts
	"""
	characters = []

	for i, char in enumerate(text):
		if char in ('O', 'C'):
			characters.append({
				'character': char,
				'x': x,
				'y': y,
				'font_family': font_family,
				'font_size': font_size,
				'font_weight': font_weight,
				'fill_color': fill,
				'source_text': source_text,
				'char_index': i
			})

	return characters
