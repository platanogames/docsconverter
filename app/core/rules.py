from __future__ import annotations

import re

from app.core.models import RuleSet


def _normalize_headings(content: str) -> str:
    """Ensure heading hierarchy is correct (h1 > h2 > h3, no jumps)."""
    lines = content.split("\n")
    result: list[str] = []
    last_level = 0
    for line in lines:
        match = re.match(r"^(#{1,6})\s", line)
        if match:
            hashes = match.group(1)
            level = len(hashes)
            if last_level == 0:
                # First heading becomes h1
                if level != 1:
                    line = "# " + line.lstrip("#").lstrip()
                    level = 1
            elif level > last_level + 1:
                # Jump detected — demote to last_level + 1
                target = last_level + 1
                line = "#" * target + " " + line.lstrip("#").lstrip()
                level = target
            last_level = level
        result.append(line)
    return "\n".join(result)


def _fix_code_fences(content: str) -> str:
    """Close unclosed code fences."""
    lines = content.split("\n")
    in_fence = False
    fence_marker = ""
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```"):
                in_fence = True
                fence_marker = "```"
        else:
            if stripped.startswith("```"):
                in_fence = False
                fence_marker = ""
        result.append(line)
    if in_fence:
        result.append(fence_marker)
    return "\n".join(result)


def _sanitize_links(content: str) -> str:
    """Remove broken or empty links."""

    def _fix_link(match: re.Match) -> str:
        text = match.group(1)
        url = match.group(2).strip()
        if not url or url in ("#", "about:blank"):
            return text
        return match.group(0)

    return re.sub(r"\[([^\]]*)\]\(([^)]*)\)", _fix_link, content)


def apply_rules(content: str, rules: RuleSet) -> str:
    if rules.normalize_headings:
        content = _normalize_headings(content)
    if rules.fix_code_fences:
        content = _fix_code_fences(content)
    if rules.sanitize_links:
        content = _sanitize_links(content)
    return content
