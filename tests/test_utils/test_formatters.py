"""Tests for formatters module using unittest methodology."""

import unittest

from netvelocimeter.cli.utils.formatters import escape_whitespace


class TestEscapeWhitespace(unittest.TestCase):
    """Test cases for escape_whitespace function."""

    def test_empty_string(self):
        """Test escape_whitespace with empty string."""
        self.assertEqual(escape_whitespace(""), "")

    def test_plain_text(self):
        """Test escape_whitespace with plain text (no special chars)."""
        text = "Hello World"
        self.assertEqual(escape_whitespace(text), text)

    def test_backslash(self):
        """Test escaping backslash character."""
        self.assertEqual(escape_whitespace(r"C:\path\to\file"), r"C:\\path\\to\\file")

    def test_newline(self):
        """Test escaping newline character."""
        self.assertEqual(escape_whitespace("line1\nline2"), r"line1\nline2")

    def test_tab(self):
        """Test escaping tab character."""
        self.assertEqual(escape_whitespace("column1\tcolumn2"), r"column1\tcolumn2")

    def test_carriage_return(self):
        """Test escaping carriage return character."""
        self.assertEqual(escape_whitespace("line1\rline2"), r"line1\rline2")

    def test_form_feed(self):
        """Test escaping form feed character."""
        self.assertEqual(escape_whitespace("page1\fpage2"), r"page1\fpage2")

    def test_vertical_tab(self):
        """Test escaping vertical tab character."""
        self.assertEqual(escape_whitespace("row1\vrow2"), r"row1\vrow2")

    def test_multiple_whitespace(self):
        """Test escaping multiple whitespace characters."""
        self.assertEqual(escape_whitespace("a\nb\tc\rd\fe\vf"), r"a\nb\tc\rd\fe\vf")
        self.assertEqual(escape_whitespace("a\r\n\t\f\vf"), r"a\r\n\t\f\vf")

    def test_mixed_content(self):
        """Test escaping mixed content with whitespace and backslashes."""
        original = "Path: C:\\temp\nContent: line1\nline2\tindented"
        expected = r"Path: C:\\temp\nContent: line1\nline2\tindented"
        self.assertEqual(escape_whitespace(original), expected)

    def test_order_of_operations(self):
        """Test correct order of operations (backslash first)."""
        # Without proper order, this would become "\\\\n" instead of "\\n"
        self.assertEqual(escape_whitespace("\\n"), r"\\n")
