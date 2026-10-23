from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_static_home_links_to_analysis_page():
    home = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert 'href="smell-report.html"' in home


def test_analysis_page_mentions_report_and_required_sections():
    page = (ROOT / "docs" / "smell-report.html").read_text(encoding="utf-8")
    assert "reports/smell-report.md" in page
    for heading in ("警告總數", "重複率", "未使用", "前端推論"):
        assert heading in page
