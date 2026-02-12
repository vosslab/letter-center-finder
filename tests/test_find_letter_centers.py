"""
Unit tests for find_letter_centers.py CLI script.
"""

import os
import sys
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import find_letter_centers


def test_import_script():
	"""Test that the script can be imported."""
	assert hasattr(find_letter_centers, 'main')
	assert hasattr(find_letter_centers, 'parse_args')


def test_parse_args_defaults():
	"""Test argument parsing with defaults."""
	sys.argv = ['find_letter_centers.py']
	args = find_letter_centers.parse_args()

	assert args.input_path == 'targets/'
	assert args.output_dir == 'output/'
	assert args.letters == 'OC'
	assert args.scale_factor == 4
	assert args.verbose is False


def test_parse_args_custom():
	"""Test argument parsing with custom values."""
	sys.argv = [
		'find_letter_centers.py',
		'-i', 'custom_input/',
		'-o', 'custom_output/',
		'-l', 'O',
		'--scale', '8',
		'-v'
	]
	args = find_letter_centers.parse_args()

	assert args.input_path == 'custom_input/'
	assert args.output_dir == 'custom_output/'
	assert args.letters == 'O'
	assert args.scale_factor == 8
	assert args.verbose is True


def test_main_nonexistent_input():
	"""Test main with nonexistent input path."""
	temp_output = tempfile.mkdtemp()

	try:
		sys.argv = [
			'find_letter_centers.py',
			'-i', '/nonexistent/path',
			'-o', temp_output
		]

		exit_code = find_letter_centers.main()
		assert exit_code == 1  # Should fail

	finally:
		shutil.rmtree(temp_output)


def test_main_single_file():
	"""Test main with single SVG file."""
	# Create temporary SVG file
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
	<text x="10" y="20" font-family="sans-serif" font-size="12">O</text>
</svg>'''

	temp_svg = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False)
	temp_svg.write(svg_content)
	temp_svg.close()

	temp_output = tempfile.mkdtemp()

	try:
		sys.argv = [
			'find_letter_centers.py',
			'-i', temp_svg.name,
			'-o', temp_output
		]

		exit_code = find_letter_centers.main()
		assert exit_code == 0  # Should succeed

		# Check output was created
		assert os.path.exists(temp_output)

	finally:
		os.unlink(temp_svg.name)
		shutil.rmtree(temp_output)


def test_main_directory():
	"""Test main with directory of SVG files."""
	# Create temporary directory with SVG file
	temp_input = tempfile.mkdtemp()
	temp_output = tempfile.mkdtemp()

	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
	<text x="10" y="20" font-family="sans-serif" font-size="12">O</text>
</svg>'''

	svg_path = os.path.join(temp_input, 'test.svg')
	with open(svg_path, 'w') as f:
		f.write(svg_content)

	try:
		sys.argv = [
			'find_letter_centers.py',
			'-i', temp_input,
			'-o', temp_output
		]

		exit_code = find_letter_centers.main()
		assert exit_code == 0  # Should succeed

		# Check summary report was created
		summary_path = os.path.join(temp_output, 'summary_report.txt')
		assert os.path.exists(summary_path)

	finally:
		shutil.rmtree(temp_input)
		shutil.rmtree(temp_output)
