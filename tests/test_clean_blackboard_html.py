import pathlib
import subprocess

import bs4


PYTHON_BIN = "/opt/homebrew/opt/python@3.12/bin/python3.12"


#============================================
def run_cleaner(repo_root: str, output_path: pathlib.Path) -> str:
	"""
	Run clean_blackboard_html.py on the known regression sample.
	"""
	input_path = pathlib.Path(repo_root) / "teaching_scripts/html_samples/Preview_Quiz_2.html"
	script_path = pathlib.Path(repo_root) / "teaching_scripts/clean_blackboard_html.py"
	subprocess.run(
		[
			PYTHON_BIN,
			str(script_path),
			"-i",
			str(input_path),
			"-o",
			str(output_path),
		],
		check=True,
		cwd=repo_root,
		capture_output=True,
		text=True,
	)
	output_html = output_path.read_text(encoding="utf-8")
	return output_html


#============================================
def find_question_div(soup: bs4.BeautifulSoup, question_number: int) -> bs4.Tag:
	"""
	Find the takeQuestionDiv for a given question number.
	"""
	target = f"Question {question_number}"
	for qdiv in soup.find_all("div", class_="takeQuestionDiv"):
		header = qdiv.find("h5")
		if not header:
			continue
		if header.get_text(strip=True) == target:
			return qdiv
	raise AssertionError(f"Could not find {target} in cleaned HTML.")


#============================================
def test_clean_blackboard_html_layout_regressions(repo_root: str, tmp_path: pathlib.Path) -> None:
	"""
	Guard against recent print-layout regressions in clean_blackboard_html.py.
	"""
	output_path = tmp_path / "Cleaned_Preview_Quiz_2_test.html"
	output_html = run_cleaner(repo_root, output_path)
	soup = bs4.BeautifulSoup(output_html, "html.parser")

	# Ensure question containers are non-scrolling; scrollbars clipped quiz images.
	for qdiv in soup.find_all("div", class_="takeQuestionDiv"):
		style = qdiv.get("style", "")
		assert "overflow:visible" in style
		assert "display:flow-root" in style

	# Ensure media choices use adaptive auto-fit grid, not fixed two-column widths.
	style_text = soup.find("style").get_text(" ", strip=True)
	assert "cleaned-choice-grid" in style_text
	assert "repeat(auto-fit, minmax" in style_text
	assert "width:48%" not in style_text
	assert "calc(50% - 20px)" not in style_text

	# Question 7 text-only choices: radio and text should stay in one inline row.
	q7 = find_question_div(soup, 7)
	labels = q7.find_all("label")
	assert labels, "Expected text-choice labels in Question 7."
	for label in labels:
		input_tag = label.find("input", attrs={"type": ["radio", "checkbox"]})
		if not input_tag:
			continue
		label_style = label.get("style", "")
		assert "display:inline-flex" in label_style
		assert "align-items:center" in label_style
		# Nested <p> tags force line breaks and split radio/text onto separate lines.
		assert not label.find("p")

	# Question 6 media choices: full image should remain visible with no clipping wrapper.
	q6 = find_question_div(soup, 6)
	media_grid = q6.find("div", class_="cleaned-choice-grid")
	assert media_grid is not None
	for card in media_grid.find_all("div", class_="cleaned-choice-item"):
		images = card.find_all("img", class_="cleaned-choice-media")
		assert images, "Expected media choice image in each Question 6 choice card."
		for wrapper in card.find_all("div"):
			wrapper_style = wrapper.get("style", "")
			assert "overflow:hidden" not in wrapper_style
