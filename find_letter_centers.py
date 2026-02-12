#!/usr/bin/env python3

"""
Analyze O and C letter glyphs in SVG files.

Fits axis-aligned ellipses and computes convex hulls for typography analysis.
"""

import sys
import os
import argparse

# Add package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from letter_center_finder import pipeline


def parse_args():
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Fit ellipses to letter glyphs in SVG files",
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  %(prog)s -i targets/ -o output/
  %(prog)s -i targets/ALLLDM_furanose_alpha.svg -o output/ -v
  %(prog)s -i targets/ -o output/ -l O --scale 8
		"""
	)

	parser.add_argument(
		'-i', '--input',
		dest='input_path',
		default='targets/',
		help='Input SVG file or directory (default: targets/)'
	)

	parser.add_argument(
		'-o', '--output',
		dest='output_dir',
		default='output/',
		help='Output directory for results (default: output/)'
	)

	parser.add_argument(
		'-l', '--letters',
		dest='letters',
		default='OC',
		help='Letters to analyze (default: OC)'
	)

	parser.add_argument(
		'--scale',
		dest='scale_factor',
		type=int,
		default=4,
		help='Rendering scale factor (default: 4)'
	)

	parser.add_argument(
		'-v', '--verbose',
		dest='verbose',
		action='store_true',
		help='Verbose output'
	)

	return parser.parse_args()


def main():
	"""Main entry point."""
	args = parse_args()

	# Validate input path
	if not os.path.exists(args.input_path):
		print(f"Error: Input path does not exist: {args.input_path}", file=sys.stderr)
		return 1

	# Create output directory
	os.makedirs(args.output_dir, exist_ok=True)

	# Determine if input is file or directory
	if os.path.isfile(args.input_path):
		# Process single file
		if args.verbose:
			print(f"Processing single file: {args.input_path}")

		result = pipeline.process_svg_file(
			args.input_path,
			args.output_dir,
			args.letters,
			args.scale_factor,
			args.verbose
		)

		if 'error' in result:
			print(f"\nError: {result['error']}", file=sys.stderr)
			return 1

		# Print summary
		print(f"\nProcessed: {result['svg_file']}")
		print(f"Characters analyzed: {len(result['characters'])}")
		successful = len([c for c in result['characters'] if 'error' not in c])
		print(f"Successful: {successful}/{len(result['characters'])}")

	elif os.path.isdir(args.input_path):
		# Process directory
		if args.verbose:
			print(f"Processing directory: {args.input_path}")

		stats = pipeline.batch_process(
			args.input_path,
			args.output_dir,
			args.letters,
			args.scale_factor,
			args.verbose
		)

		if 'error' in stats:
			print(f"\nError: {stats['error']}", file=sys.stderr)
			return 1

		# Print summary
		print("\n" + "=" * 60)
		print("SUMMARY")
		print("=" * 60)
		print(f"Files processed: {stats['files_processed']}")
		print(f"Total characters: {stats['total_characters']}")
		print(f"Successful: {stats['successful_characters']}")
		print(f"Failed: {stats['failed_characters']}")
		print(f"\nResults saved to: {args.output_dir}")

	else:
		print(f"Error: Input path is neither file nor directory: {args.input_path}", file=sys.stderr)
		return 1

	return 0


if __name__ == '__main__':
	sys.exit(main())
