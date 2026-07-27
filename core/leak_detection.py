"""Helpers for matching sensitive numeric values in model-formatted text."""

import re


_THOUSANDS_SEPARATOR = re.compile(r"(?<=\d),(?=\d{3}\b)")


def normalize_numeric_formatting(text):
    """Normalize common LLM number formatting without changing other text."""
    return _THOUSANDS_SEPARATOR.sub("", str(text or ""))


def find_sensitive_values(text, sensitive_values):
    """Return canonical values found despite commas or currency prefixes."""
    normalized = normalize_numeric_formatting(text)
    return {
        str(value)
        for value in sensitive_values
        if str(value) in normalized
    }
