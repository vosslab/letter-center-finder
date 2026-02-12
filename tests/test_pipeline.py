"""
Unit tests for pipeline module.
"""

import os
import json
import tempfile
import shutil
import pytest
from letter_center_finder import pipeline


@pytest.fixture
def temp_output_dir():
	"""Create temporary output directory."""
	temp_dir = tempfile.mkdtemp()
	yield temp_dir
	shutil.rmtree(temp_dir)


@pytest.fixture
def sample_svg_file():
	"""Create a sample SVG file for testing."""
	svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
	<text x="10" y="20" font-family="sans-serif" font-size="12" fill="#000">O</text>
	<text x="30" y="20" font-family="sans-serif" font-size="12" fill="#000">C</text>
</svg>'''

	with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
		f.write(svg_content)
		temp_path = f.name

	yield temp_path
	os.unlink(temp_path)


def test_process_single_character(temp_output_dir):
	"""Test processing a single character."""
	char_metadata = {
		'character': 'O',
		'x': 10.0,
		'y': 20.0,
		'cx': 13.72,
		'cy': 16.28,
		'font_family': 'sans-serif',
		'font_size': 12.0,
		'font_weight': 'normal',
		'fill_color': '#000000',
		'source_text': 'O'
	}

	result = pipeline.process_single_character(
		char_metadata,
		temp_output_dir,
		char_index=0,
		scale_factor=4,
		verbose=False
	)

	assert 'char' in result
	assert result['char'] == 'O'
	assert 'ellipse' in result
	assert 'convex_hull' in result
	assert 'fit_quality' in result
	assert 'diagnostic_file' in result

	# Check diagnostic file was created
	diagnostic_path = os.path.join(temp_output_dir, result['diagnostic_file'])
	assert os.path.exists(diagnostic_path)


def test_process_svg_file(sample_svg_file, temp_output_dir):
	"""Test processing a complete SVG file."""
	result = pipeline.process_svg_file(
		sample_svg_file,
		temp_output_dir,
		target_letters='OC',
		scale_factor=4,
		verbose=False
	)

	assert 'svg_file' in result
	assert 'characters' in result
	assert len(result['characters']) == 2

	# Check that results.json was created
	svg_basename = os.path.splitext(os.path.basename(sample_svg_file))[0]
	results_path = os.path.join(temp_output_dir, svg_basename, 'results.json')
	assert os.path.exists(results_path)

	# Verify JSON content
	with open(results_path) as f:
		data = json.load(f)
		assert 'svg_file' in data
		assert 'characters' in data

	# Check that summary.txt was created
	summary_path = os.path.join(temp_output_dir, svg_basename, 'summary.txt')
	assert os.path.exists(summary_path)


def test_process_svg_file_filter_letters(sample_svg_file, temp_output_dir):
	"""Test filtering specific letters."""
	# Only process O, not C
	result = pipeline.process_svg_file(
		sample_svg_file,
		temp_output_dir,
		target_letters='O',
		scale_factor=4,
		verbose=False
	)

	# Should only have 1 character (O)
	assert len(result['characters']) == 1
	assert result['characters'][0]['char'] == 'O'


def test_batch_process(temp_output_dir):
	"""Test batch processing of directory."""
	# Create temporary directory with multiple SVG files
	temp_input_dir = tempfile.mkdtemp()

	try:
		# Create two sample SVG files
		for i in range(2):
			svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
	<text x="10" y="20" font-family="sans-serif" font-size="12">O</text>
</svg>'''
			with open(os.path.join(temp_input_dir, f'test_{i}.svg'), 'w') as f:
				f.write(svg_content)

		stats = pipeline.batch_process(
			temp_input_dir,
			temp_output_dir,
			target_letters='O',
			scale_factor=4,
			verbose=False
		)

		assert 'files_processed' in stats
		assert stats['files_processed'] == 2
		assert stats['total_characters'] == 2
		assert stats['successful_characters'] == 2

		# Check summary report was created
		summary_path = os.path.join(temp_output_dir, 'summary_report.txt')
		assert os.path.exists(summary_path)

	finally:
		shutil.rmtree(temp_input_dir)


def test_batch_process_empty_directory(temp_output_dir):
	"""Test batch processing with no SVG files."""
	# Create empty directory
	temp_input_dir = tempfile.mkdtemp()

	try:
		stats = pipeline.batch_process(
			temp_input_dir,
			temp_output_dir,
			verbose=False
		)

		assert 'error' in stats
		assert stats['files_processed'] == 0

	finally:
		shutil.rmtree(temp_input_dir)
