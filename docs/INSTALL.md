# Install

This repo is run from source. "Installed" means: Python dependencies are
available, `rsvg-convert` is on `PATH`, and `find_letter_centers.py` runs
without import errors.

## Requirements

- Python 3 (tested with 3.12)
- `rsvg-convert` from librsvg (used for SVG rendering with native font fidelity)
- Python packages listed in [pip_requirements.txt](../pip_requirements.txt)

## System dependencies

Install `rsvg-convert` via your system package manager:

```bash
# macOS (Homebrew)
brew install librsvg

# Debian / Ubuntu
sudo apt-get install librsvg2-bin
```

## Install steps

```bash
git clone <repo-url> && cd letter-center-finder
pip install -r pip_requirements.txt
```

## Verify install

```bash
python find_letter_centers.py --help
```

This should print the CLI help text with flags and examples. If it fails with
an import error, a Python dependency is missing. If processing fails later at
runtime with `rsvg-convert failed`, librsvg is not installed or not on `PATH`.

## Known gaps

- [ ] Confirm minimum Python version (3.12 is tested; lower bounds unknown)
- [ ] Confirm librsvg version requirements, if any
