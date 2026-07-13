from app.core.models import RuleSet
from app.core.rules import apply_rules


def test_normalize_headings_fixes_first_heading() -> None:
    content = "## Should be h1\n### Sub"
    result = apply_rules(content, RuleSet(normalize_headings=True, fix_code_fences=False))
    assert result.startswith("# Should be h1")


def test_normalize_headings_fixes_jump() -> None:
    content = "# Title\n#### Jumped to h4"
    result = apply_rules(content, RuleSet(normalize_headings=True, fix_code_fences=False))
    lines = result.split("\n")
    assert lines[1].startswith("## ")


def test_fix_code_fences_closes_unclosed() -> None:
    content = "```python\nprint('hello')\n"
    result = apply_rules(content, RuleSet(normalize_headings=False, fix_code_fences=True))
    assert result.endswith("```")


def test_fix_code_fences_no_change_when_closed() -> None:
    content = "```python\nprint('hello')\n```"
    result = apply_rules(content, RuleSet(normalize_headings=False, fix_code_fences=True))
    assert result == content


def test_sanitize_links_removes_empty_urls() -> None:
    content = "Click [here](#) for info"
    result = apply_rules(content, RuleSet(normalize_headings=False, fix_code_fences=False, sanitize_links=True))
    assert "[here](#)" not in result
    assert "here" in result


def test_sanitize_links_keeps_valid_urls() -> None:
    content = "Visit [site](https://example.com)"
    result = apply_rules(content, RuleSet(normalize_headings=False, fix_code_fences=False, sanitize_links=True))
    assert "[site](https://example.com)" in result
