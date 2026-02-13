# letter-center-finder

Find the geometric center of O and C letter glyphs inside SVG chemical structure
diagrams and fit axis-aligned ellipses to each glyph outline. Built for
typography analysis of sugar ring diagrams where precise glyph geometry is needed.

## Quick start

```bash
pip install -r pip_requirements.txt
brew install librsvg

python find_letter_centers.py -i targets/ -o output/
```

## Usage

Process a single SVG file:

```bash
python find_letter_centers.py -i targets/ALLLDM_furanose_alpha.svg -o output/ -v
```

Process a directory of SVG files, analyzing only O glyphs:

```bash
python find_letter_centers.py -i targets/ -o output/ -l O
```

Flags: `-i` input path, `-o` output directory, `-l` letters to analyze (default
`OC`), `-z` render zoom factor (default 10), `-v` verbose.

## Testing

```bash
pytest
```

## Documentation

- [docs/INSTALL.md](docs/INSTALL.md): setup steps, dependencies, and verify command
- [docs/USAGE.md](docs/USAGE.md): CLI flags, examples, and input/output details
- [docs/PROJECT_GOALS.md](docs/PROJECT_GOALS.md): goals, strategies (v1 failed, v2 implemented), and quantitative success criteria
- [docs/CHANGELOG.md](docs/CHANGELOG.md): chronological record of changes
- [docs/PYTHON_STYLE.md](docs/PYTHON_STYLE.md): Python formatting and linting conventions
- [docs/REPO_STYLE.md](docs/REPO_STYLE.md): repo-level organization and file placement rules
- [docs/MARKDOWN_STYLE.md](docs/MARKDOWN_STYLE.md): Markdown writing rules
- [docs/AUTHORS.md](docs/AUTHORS.md): maintainers and contributors

## Status

Experimental. The v2 per-character SVG isolation approach processes all 6 target
SVG files (44 characters, 0 failures). See
[docs/CHANGELOG.md](docs/CHANGELOG.md) for current results.

## Maintainer

Neil Voss -- <https://bsky.app/profile/neilvosslab.bsky.social>
