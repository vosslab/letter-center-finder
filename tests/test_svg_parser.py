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
		# x is now cursor position (left edge of char), should equal the text x for single chars
		assert chars[0]['x'] == 10.0
		assert chars[1]['x'] == 30.0
		# cx/cy should be present and centered
		assert 'cx' in chars[0]
		assert 'cy' in chars[0]
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
		# O is at index 1, C is at index 4 - O should be left of C
		assert o_chars[0]['cx'] < c_chars[0]['cx']
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


# === Font metric function tests ===

def test_glyph_char_advance_known_chars():
	"""Test character advance widths for specific character groups."""
	fs = 12.0
	# Narrow chars
	assert svg_parser._glyph_char_advance(fs, 'I') == fs * 0.38
	assert svg_parser._glyph_char_advance(fs, 'L') == fs * 0.38
	# Wide chars
	assert svg_parser._glyph_char_advance(fs, 'W') == fs * 0.82
	assert svg_parser._glyph_char_advance(fs, 'M') == fs * 0.82
	# O/C group
	assert svg_parser._glyph_char_advance(fs, 'O') == fs * 0.62
	assert svg_parser._glyph_char_advance(fs, 'C') == fs * 0.62
	# H/N group
	assert svg_parser._glyph_char_advance(fs, 'H') == fs * 0.58
	# Lowercase
	assert svg_parser._glyph_char_advance(fs, 'a') == fs * 0.50


def test_glyph_char_advance_minimum_size():
	"""Test that advance width clamps font_size to minimum of 1.0."""
	# Even with tiny font_size, should use 1.0
	assert svg_parser._glyph_char_advance(0.0, 'O') == 1.0 * 0.62
	assert svg_parser._glyph_char_advance(-5.0, 'O') == 1.0 * 0.62


def test_glyph_char_vertical_bounds_oc():
	"""Test vertical bounds for O and C characters."""
	baseline = 100.0
	fs = 12.0
	top_o, bot_o = svg_parser._glyph_char_vertical_bounds(baseline, fs, 'O')
	top_c, bot_c = svg_parser._glyph_char_vertical_bounds(baseline, fs, 'C')
	# O and C use the same bounds (both in the rounded group)
	assert top_o == top_c
	assert bot_o == bot_c
	# Top should be above baseline
	assert top_o < baseline
	# Bottom should be below baseline
	assert bot_o > baseline
	# Specific values
	assert abs(top_o - (baseline - fs * 0.78)) < 1e-9
	assert abs(bot_o - (baseline + fs * 0.16)) < 1e-9


def test_glyph_char_vertical_bounds_other():
	"""Test vertical bounds for non-OC characters."""
	baseline = 100.0
	fs = 12.0
	top_h, bot_h = svg_parser._glyph_char_vertical_bounds(baseline, fs, 'H')
	assert abs(top_h - (baseline - fs * 0.80)) < 1e-9
	assert abs(bot_h - (baseline + fs * 0.20)) < 1e-9


def test_glyph_text_width():
	"""Test total text width calculation."""
	fs = 10.0
	# Single char - no tracking
	w_single = svg_parser._glyph_text_width('O', fs)
	assert abs(w_single - svg_parser._glyph_char_advance(fs, 'O')) < 1e-9

	# Two chars - one tracking gap
	tracking = fs * 0.04
	w_two = svg_parser._glyph_text_width('OH', fs)
	expected = svg_parser._glyph_char_advance(fs, 'O') + svg_parser._glyph_char_advance(fs, 'H') + tracking
	assert abs(w_two - expected) < 1e-9


def test_glyph_text_width_empty():
	"""Test text width of empty string."""
	assert svg_parser._glyph_text_width('', 12.0) == 0.0


# === text-anchor handling tests ===

def test_text_anchor_start():
	"""Test text-anchor='start' (default): x is left edge."""
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
	<text x="50" y="40" font-size="12" text-anchor="start">O</text>
</svg>'''

	with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
		f.write(svg_content)
		temp_path = f.name

	try:
		chars = svg_parser.parse_svg_file(temp_path)
		assert len(chars) == 1
		# For start anchor, cursor starts at x=50
		# cx should be x + advance/2
		advance = svg_parser._glyph_char_advance(12.0, 'O')
		expected_cx = 50.0 + advance * 0.5
		assert abs(chars[0]['cx'] - expected_cx) < 1e-9
	finally:
		os.unlink(temp_path)


def test_text_anchor_end():
	"""Test text-anchor='end': x is right edge of text."""
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
	<text x="100" y="40" font-size="12" text-anchor="end">HO</text>
</svg>'''

	with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
		f.write(svg_content)
		temp_path = f.name

	try:
		chars = svg_parser.parse_svg_file(temp_path)
		assert len(chars) == 1
		assert chars[0]['character'] == 'O'
		# For end anchor, cursor starts at x - text_width
		# O center should be left of x=100
		assert chars[0]['cx'] < 100.0
		# Verify the O center is within the text span
		text_width = svg_parser._glyph_text_width('HO', 12.0)
		left_edge = 100.0 - text_width
		assert chars[0]['cx'] > left_edge
	finally:
		os.unlink(temp_path)


def test_text_anchor_middle():
	"""Test text-anchor='middle': x is center of text."""
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
	<text x="100" y="40" font-size="12" text-anchor="middle">O</text>
</svg>'''

	with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
		f.write(svg_content)
		temp_path = f.name

	try:
		chars = svg_parser.parse_svg_file(temp_path)
		assert len(chars) == 1
		# For single char with middle anchor, cx should be very close to x
		# (text_width/2 shifts left, then advance/2 shifts right - these are the same for single char)
		assert abs(chars[0]['cx'] - 100.0) < 1e-9
	finally:
		os.unlink(temp_path)


def test_text_anchor_end_ho_o_is_left_of_x():
	"""Verify 'HO' with text-anchor='end' places O center to the left of x."""
	fs = 12.0
	x = 100.0
	chars = svg_parser._extract_chars_from_string(
		'HO', x, 50.0, 'end', 'sans-serif', fs, 'normal', '#000', 'HO'
	)
	assert len(chars) == 1
	assert chars[0]['character'] == 'O'
	# O center must be strictly left of the anchor point
	assert chars[0]['cx'] < x


# === cx/cy center position verification tests ===

def test_cx_is_horizontally_centered_in_char():
	"""Verify cx is at the horizontal center of the character advance."""
	fs = 14.0
	chars = svg_parser._extract_chars_from_string(
		'O', 10.0, 50.0, 'start', 'sans-serif', fs, 'normal', '#000', 'O'
	)
	assert len(chars) == 1
	advance = svg_parser._glyph_char_advance(fs, 'O')
	expected_cx = 10.0 + advance * 0.5
	assert abs(chars[0]['cx'] - expected_cx) < 1e-9


def test_cy_is_vertically_centered():
	"""Verify cy is midpoint of top_y and bottom_y bounds."""
	fs = 14.0
	baseline_y = 50.0
	chars = svg_parser._extract_chars_from_string(
		'O', 10.0, baseline_y, 'start', 'sans-serif', fs, 'normal', '#000', 'O'
	)
	assert len(chars) == 1
	top_y, bottom_y = svg_parser._glyph_char_vertical_bounds(baseline_y, fs, 'O')
	expected_cy = (top_y + bottom_y) * 0.5
	assert abs(chars[0]['cy'] - expected_cy) < 1e-9


def test_cy_is_above_baseline():
	"""Center of O/C should be above the baseline (smaller y in SVG coords)."""
	fs = 12.0
	baseline_y = 50.0
	for char_text in ('O', 'C'):
		chars = svg_parser._extract_chars_from_string(
			char_text, 10.0, baseline_y, 'start', 'sans-serif', fs, 'normal', '#000', char_text
		)
		assert len(chars) == 1
		# The vertical center should be above the baseline (ascent > descent)
		assert chars[0]['cy'] < baseline_y, f"{char_text} center should be above baseline"


def test_composite_oh_positions():
	"""In 'OH', O should be left of H's position, both offset from x correctly."""
	fs = 12.0
	x = 20.0
	chars = svg_parser._extract_chars_from_string(
		'OH', x, 50.0, 'start', 'sans-serif', fs, 'normal', '#000', 'OH'
	)
	assert len(chars) == 1
	assert chars[0]['character'] == 'O'
	# O is first char, so its cx should be x + advance_O/2
	advance_o = svg_parser._glyph_char_advance(fs, 'O')
	expected_cx = x + advance_o * 0.5
	assert abs(chars[0]['cx'] - expected_cx) < 1e-9


def test_composite_ho_positions():
	"""In 'HO', O is second char - its center should be offset past H's advance."""
	fs = 12.0
	x = 20.0
	tracking = fs * 0.04
	chars = svg_parser._extract_chars_from_string(
		'HO', x, 50.0, 'start', 'sans-serif', fs, 'normal', '#000', 'HO'
	)
	assert len(chars) == 1
	assert chars[0]['character'] == 'O'
	advance_h = svg_parser._glyph_char_advance(fs, 'H')
	advance_o = svg_parser._glyph_char_advance(fs, 'O')
	expected_cx = x + advance_h + tracking + advance_o * 0.5
	assert abs(chars[0]['cx'] - expected_cx) < 1e-9


def test_multiple_oc_in_text():
	"""Test that multiple O/C chars in same string each get distinct, correct centers."""
	fs = 10.0
	x = 0.0
	tracking = fs * 0.04
	chars = svg_parser._extract_chars_from_string(
		'COC', x, 30.0, 'start', 'sans-serif', fs, 'normal', '#000', 'COC'
	)
	assert len(chars) == 3
	assert chars[0]['character'] == 'C'
	assert chars[1]['character'] == 'O'
	assert chars[2]['character'] == 'C'
	# Each center should be strictly increasing in x
	assert chars[0]['cx'] < chars[1]['cx'] < chars[2]['cx']
	# First C at index 0
	adv_c = svg_parser._glyph_char_advance(fs, 'C')
	adv_o = svg_parser._glyph_char_advance(fs, 'O')
	assert abs(chars[0]['cx'] - (x + adv_c * 0.5)) < 1e-9
	# O at index 1: after C advance + tracking
	cursor_after_c = x + adv_c + tracking
	assert abs(chars[1]['cx'] - (cursor_after_c + adv_o * 0.5)) < 1e-9
	# C at index 2: after C + tracking + O + tracking
	cursor_after_o = cursor_after_c + adv_o + tracking
	assert abs(chars[2]['cx'] - (cursor_after_o + adv_c * 0.5)) < 1e-9


def test_text_anchor_middle_multi_char():
	"""For 'OCO' with middle anchor, text center should be near x."""
	fs = 10.0
	x = 50.0
	chars = svg_parser._extract_chars_from_string(
		'OCO', x, 30.0, 'middle', 'sans-serif', fs, 'normal', '#000', 'OCO'
	)
	assert len(chars) == 3
	# The middle char (C at index 1) center should be very close to x
	# since all three chars have the same advance (O, C are in same group)
	middle_cx = chars[1]['cx']
	assert abs(middle_cx - x) < fs * 0.1  # within 10% of font size


def test_text_anchor_from_style_attribute():
	"""Test that text-anchor in CSS style is parsed."""
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
	<text x="100" y="40" font-size="12" style="text-anchor:end">HO</text>
</svg>'''

	with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
		f.write(svg_content)
		temp_path = f.name

	try:
		chars = svg_parser.parse_svg_file(temp_path)
		assert len(chars) == 1
		assert chars[0]['character'] == 'O'
		# With end anchor at x=100, O center should be left of 100
		assert chars[0]['cx'] < 100.0
	finally:
		os.unlink(temp_path)
