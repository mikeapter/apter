"""
Tests for shared validation logic (mirrors frontend validation.ts).

Run: pytest tests/unit/test_validation.py -v
"""
import re
import pytest


# Mirror the backend name pattern
_NAME_PATTERN = re.compile(r"^[a-zA-Z\s'\-]{2,50}$")


def validate_name(value: str) -> str | None:
    """Python mirror of frontend validateName."""
    trimmed = value.strip()
    if not trimmed:
        return "Required"
    if len(trimmed) < 2:
        return "Must be at least 2 characters"
    if len(trimmed) > 50:
        return "Must be 50 characters or fewer"
    if not _NAME_PATTERN.match(trimmed):
        return "Only letters, spaces, hyphens, and apostrophes"
    return None


def validate_email(value: str) -> str | None:
    """Python mirror of frontend validateEmail."""
    trimmed = value.strip()
    if not trimmed:
        return "Required"
    email_pattern = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    if not email_pattern.match(trimmed):
        return "Enter a valid email address"
    return None


def validate_password(value: str) -> str | None:
    """Python mirror of frontend validatePassword."""
    if not value:
        return "Required"
    if len(value) < 10:
        return "Must be at least 10 characters"
    return None


class TestNameValidation:
    def test_valid_name(self):
        assert validate_name("John") is None

    def test_valid_hyphenated(self):
        assert validate_name("O'Brien-Smith") is None

    def test_empty(self):
        assert validate_name("") == "Required"

    def test_too_short(self):
        assert validate_name("J") == "Must be at least 2 characters"

    def test_too_long(self):
        assert validate_name("A" * 51) == "Must be 50 characters or fewer"

    def test_numbers_rejected(self):
        assert validate_name("John123") is not None

    def test_special_chars_rejected(self):
        assert validate_name("John@Doe") is not None

    def test_spaces_allowed(self):
        assert validate_name("Mary Jane") is None


class TestEmailValidation:
    def test_valid_email(self):
        assert validate_email("user@example.com") is None

    def test_empty(self):
        assert validate_email("") == "Required"

    def test_no_at_sign(self):
        assert validate_email("userexample.com") is not None

    def test_no_domain(self):
        assert validate_email("user@") is not None


class TestPasswordValidation:
    def test_valid_password(self):
        assert validate_password("StrongPass1!") is None

    def test_empty(self):
        assert validate_password("") == "Required"

    def test_too_short(self):
        assert validate_password("short") == "Must be at least 10 characters"

    def test_exactly_10_chars(self):
        assert validate_password("1234567890") is None
