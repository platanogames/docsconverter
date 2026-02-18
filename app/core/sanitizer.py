from __future__ import annotations

import re

from pydantic import BaseModel, Field


class SanitizationRule(BaseModel):
    name: str = ""
    pattern: str = ""
    action: str = "remove_line"  # remove_line | remove_match | replace
    replacement_text: str = ""
    is_regex: bool = False
    scope: str = "all"  # all | outside_code
    enabled: bool = True


class SanitizationConfig(BaseModel):
    rules: list[SanitizationRule] = Field(default_factory=list)
    save_cleaned: bool = True
    validate_after_cleaning: bool = True
    wrap_long_code_lines: bool = False
    max_code_line_length: int = 85
    code_break_at: int = 80


class MarkdownSanitizer:
    def __init__(self, config: SanitizationConfig) -> None:
        self.config = config

    def sanitize(self, content: str) -> tuple[str, dict]:
        stats = {"lines_removed": 0, "matches_removed": 0, "replacements_made": 0}
        active_rules = [r for r in self.config.rules if r.enabled]

        for rule in active_rules:
            content, rule_stats = self._apply_rule(content, rule)
            stats["lines_removed"] += rule_stats["lines_removed"]
            stats["matches_removed"] += rule_stats["matches_removed"]
            stats["replacements_made"] += rule_stats["replacements_made"]

        if self.config.wrap_long_code_lines:
            content = self._wrap_code_lines(content)

        return content, stats

    def _apply_rule(self, content: str, rule: SanitizationRule) -> tuple[str, dict]:
        stats = {"lines_removed": 0, "matches_removed": 0, "replacements_made": 0}

        if rule.scope == "outside_code":
            return self._apply_outside_code(content, rule, stats)

        # scope == "all"
        if rule.action == "remove_line":
            content, count = self._remove_lines(content, rule)
            stats["lines_removed"] += count
        elif rule.action == "remove_match":
            content, count = self._remove_matches(content, rule)
            stats["matches_removed"] += count
        elif rule.action == "replace":
            content, count = self._replace_matches(content, rule)
            stats["replacements_made"] += count

        return content, stats

    def _apply_outside_code(
        self, content: str, rule: SanitizationRule, stats: dict
    ) -> tuple[str, dict]:
        lines = content.split("\n")
        result: list[str] = []
        in_code = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code = not in_code
                result.append(line)
                continue
            if in_code:
                result.append(line)
                continue
            # Apply rule to this line
            if rule.action == "remove_line":
                pattern = re.compile(rule.pattern) if rule.is_regex else None
                if pattern and pattern.search(line):
                    stats["lines_removed"] += 1
                    continue
                if not rule.is_regex and rule.pattern in line:
                    stats["lines_removed"] += 1
                    continue
            elif rule.action == "remove_match":
                if rule.is_regex:
                    new_line, n = re.subn(rule.pattern, "", line)
                else:
                    n = line.count(rule.pattern)
                    new_line = line.replace(rule.pattern, "")
                stats["matches_removed"] += n
                line = new_line
            elif rule.action == "replace":
                replacement = rule.replacement_text
                if rule.is_regex:
                    new_line, n = re.subn(rule.pattern, replacement, line)
                else:
                    n = line.count(rule.pattern)
                    new_line = line.replace(rule.pattern, replacement)
                stats["replacements_made"] += n
                line = new_line
            result.append(line)
        return "\n".join(result), stats

    @staticmethod
    def _remove_lines(content: str, rule: SanitizationRule) -> tuple[str, int]:
        lines = content.split("\n")
        result: list[str] = []
        count = 0
        pattern = re.compile(rule.pattern) if rule.is_regex else None
        for line in lines:
            matched = False
            if pattern:
                matched = bool(pattern.search(line))
            else:
                matched = rule.pattern in line
            if matched:
                count += 1
            else:
                result.append(line)
        return "\n".join(result), count

    @staticmethod
    def _remove_matches(content: str, rule: SanitizationRule) -> tuple[str, int]:
        if rule.is_regex:
            result, count = re.subn(rule.pattern, "", content)
        else:
            count = content.count(rule.pattern)
            result = content.replace(rule.pattern, "")
        return result, count

    @staticmethod
    def _replace_matches(content: str, rule: SanitizationRule) -> tuple[str, int]:
        replacement = rule.replacement_text
        if rule.is_regex:
            result, count = re.subn(rule.pattern, replacement, content)
        else:
            count = content.count(rule.pattern)
            result = content.replace(rule.pattern, replacement)
        return result, count

    def _wrap_code_lines(self, content: str) -> str:
        lines = content.split("\n")
        result: list[str] = []
        in_code = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code = not in_code
                result.append(line)
                continue
            if in_code and len(line) > self.config.max_code_line_length:
                wrapped = self._break_line(line)
                result.extend(wrapped)
            else:
                result.append(line)
        return "\n".join(result)

    def _break_line(self, line: str) -> list[str]:
        max_len = self.config.max_code_line_length
        break_at = self.config.code_break_at
        parts: list[str] = []
        while len(line) > max_len:
            cut = break_at
            # Try to break at a space
            space_idx = line.rfind(" ", 0, max_len)
            if space_idx > 0:
                cut = space_idx + 1
            parts.append(line[:cut])
            line = line[cut:]
        parts.append(line)
        return parts
