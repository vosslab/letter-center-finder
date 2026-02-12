"""
Unit tests for svg_parser module.
"""

import os
import tempfile
from letter_center_finder import svg_parser


def test_parse_simple_svg():
	"""Test parsing simple SVG with O and C characters."""
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
	<text x="10" y="20" font-family="sans-serif" font-size="12" fill="#000">O</text>
	<text x="30" y="20" font-family="sans-serif" font-size="12" fill="#000">C</text>
</svg>'''

	with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
		f.write(svg_content)
		temp_path = f.name

	try:
		chars = svg_parser.parse_svg_file(temp_path)
		assert len(chars) == 2
		assert chars[0]['character'] == 'O'
		assert chars[1]['character'] == 'C'
		assert chars[0]['x'] == 10.0
		assert chars[1]['x'] == 30.0
	finally:
		os.unlink(temp_path)


def test_parse_tspan_svg():
	"""Test parsing SVG with tspan elements."""
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
	<text x="10" y="20" font-family="sans-serif" font-size="12">
		<tspan>H</tspan>
		<tspan>O</tspan>
		<tspan>H</tspan>
	</text>
</svg>'''

	with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
		f.write(svg_content)
		temp_path = f.name

	try:
		chars = svg_parser.parse_svg_file(temp_path)
		assert len(chars) == 1
		assert chars[0]['character'] == 'O'
	finally:
		os.unlink(temp_path)


def test_parse_composite_text():
	"""Test parsing composite text like HOH2C."""
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
	<text x="10" y="20" font-family="sans-serif" font-size="12">HOH2C</text>
</svg>'''

	with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
		f.write(svg_content)
		temp_path = f.name

	try:
		chars = svg_parser.parse_svg_file(temp_path)
		# Should find 1 O and 1 C in "HOH2C"
		assert len(chars) == 2
		o_chars = [c for c in chars if c['character'] == 'O']
		c_chars = [c for c in chars if c['character'] == 'C']
		assert len(o_chars) == 1
		assert len(c_chars) == 1
	finally:
		os.unlink(temp_path)


def test_font_attribute_inheritance():
	"""Test that tspan inherits font attributes from parent text element."""
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
	<text x="10" y="20" font-family="Arial" font-size="14" font-weight="bold">
		<tspan>O</tspan>
	</text>
</svg>'''

	with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
		f.write(svg_content)
		temp_path = f.name

	try:
		chars = svg_parser.parse_svg_file(temp_path)
		assert len(chars) == 1
		assert chars[0]['font_family'] == 'Arial'
		assert chars[0]['font_size'] == 14.0
		assert chars[0]['font_weight'] == 'bold'
	finally:
		os.unlink(temp_path)


def test_parse_style_attribute():
	"""Test parsing CSS style attributes."""
	style = "font-family:Arial;font-size:12px;fill:#000000"
	result = svg_parser.parse_style_attribute(style)

	assert result['font-family'] == 'Arial'
	assert result['font-size'] == '12px'
	assert result['fill'] == '#000000'


def test_no_target_characters():
	"""Test SVG with no O or C characters."""
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
	<text x="10" y="20" font-family="sans-serif" font-size="12">HELLO</text>
</svg>'''

	with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
		f.write(svg_content)
		temp_path = f.name

	try:
		chars = svg_parser.parse_svg_file(temp_path)
		# Should find 1 O (in "HELLO")
		assert len(chars) == 1
		assert chars[0]['character'] == 'O'
	finally:
		os.unlink(temp_path)
