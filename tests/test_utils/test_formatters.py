"""Tests for formatters module using unittest methodology."""

from dataclasses import dataclass
import unittest

from netvelocimeter.cli.utils.formatters import escape_whitespace
from netvelocimeter.utils.formatters import _flatten_fields, pretty_print_two_columns


@dataclass
class Simple:
    """Simple dataclass for testing."""

    a: int
    bb: str


@dataclass
class Nested:
    """Nested dataclass for testing."""

    x: int
    y: Simple
    z: str = "zzz"


@dataclass
class DeepNested:
    """Deeply nested dataclass for testing."""

    outer: Nested
    value: int


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


class TestFormattersFlattenFields(unittest.TestCase):
    """Test cases for _flatten_fields function."""

    def test_flatten_simple(self):
        """Test flattening a simple dataclass."""
        obj = Simple(a=1, bb="foo")
        fields, width = _flatten_fields(obj)
        self.assertEqual(fields, [("a:", 1), ("bb:", "foo")])
        self.assertEqual(width, 3)

    def test_flatten_nested(self):
        """Test flattening a nested dataclass."""
        obj = Nested(x=42, y=Simple(a=7, bb="bar"))
        fields, width = _flatten_fields(obj)
        # Should flatten all fields, including nested
        expected_fields = [
            ("x:", 42),
            ("a:", 7),
            ("bb:", "bar"),
            ("z:", "zzz"),
        ]
        self.assertTrue(all(pair in fields for pair in expected_fields))
        self.assertGreaterEqual(width, 3)

    def test_flatten_deep_nested(self):
        """Test flattening a deeply nested dataclass."""
        obj = DeepNested(outer=Nested(x=1, y=Simple(a=2, bb="b")), value=99)
        fields, width = _flatten_fields(obj)
        # Should include all nested fields
        expected_labels = {"x:", "a:", "bb:", "z:", "value:"}
        actual_labels = {label for label, _ in fields}
        self.assertTrue(expected_labels == actual_labels)
        self.assertGreaterEqual(width, 6)

    def test_flatten_with_prefix(self):
        """Test flattening with a prefix for field names."""
        obj = Simple(a=5, bb="test")
        fields, width = _flatten_fields(obj, prefix="pre_")
        self.assertIn(("pre_a:", 5), fields)
        self.assertIn(("pre_bb:", "test"), fields)
        self.assertGreaterEqual(width, 7)

    def test_flatten_skips_none_and_private(self):
        """Test flattening skips None and private fields."""

        @dataclass
        class WithNone:
            a: int
            bb: str | None = None
            _private: int = 123

        obj = WithNone(a=1)
        fields, width = _flatten_fields(obj)
        self.assertEqual(fields, [("a:", 1)])
        self.assertEqual(width, 2)

    def test_flatten_with_format_prefix(self):
        """Test flattening uses _format_prefix attribute for nested dataclasses."""

        @dataclass
        class WithPrefix:
            _format_prefix: str = "P_"
            a: int = 1
            bb: str = "foo"

        @dataclass
        class Outer:
            x: int
            y: WithPrefix

        obj = Outer(x=10, y=WithPrefix(a=2, bb="bar"))
        fields, width = _flatten_fields(obj)
        # The nested WithPrefix fields should be prefixed with "P_"
        self.assertIn(("P_a:", 2), fields)
        self.assertIn(("P_bb:", "bar"), fields)
        # The outer field should not be prefixed
        self.assertIn(("x:", 10), fields)
        self.assertGreaterEqual(width, 5)


class TestFormattersPrettyPrintTwoColumns(unittest.TestCase):
    """Test cases for pretty_print_two_columns function."""

    def test_pretty_print_simple(self):
        """Test pretty printing a simple dataclass."""
        obj = Simple(a=1, bb="foo")
        result = pretty_print_two_columns(obj, "")
        self.assertIn("a:  1", result)
        self.assertIn("bb: foo", result)
        self.assertEqual(len(result.splitlines()), 2)

    def test_pretty_print_nested(self):
        """Test pretty printing a nested dataclass."""
        obj = Nested(x=2, y=Simple(a=3, bb="bar"))
        result = pretty_print_two_columns(obj, "")
        self.assertIn("x:  2", result)
        self.assertIn("a:  3", result)
        self.assertIn("bb: bar", result)
        self.assertIn("z:  zzz", result)
        self.assertGreaterEqual(len(result.splitlines()), 4)

    def test_pretty_print_with_prefix(self):
        """Test pretty printing with a prefix for field names."""
        obj = Simple(a=10, bb="baz")
        result = pretty_print_two_columns(obj, prefix="P_")
        self.assertIn("P_a:  10", result)
        self.assertIn("P_bb: baz", result)

    def test_pretty_print_multiline_value(self):
        """Test pretty printing with multiline values."""

        class Multi:
            def __init__(self):
                self.a = ["line1", "line2", "line3"]

        obj = Multi()
        result = pretty_print_two_columns(obj, "")
        lines = result.splitlines()
        self.assertEqual("a: line1", lines[0])
        self.assertEqual("   line2", lines[1])
        self.assertEqual("   line3", lines[2])

    def test_pretty_print_empty_object(self):
        """Test pretty printing an empty object."""

        class Empty:
            pass

        obj = Empty()
        result = pretty_print_two_columns(obj, "")
        self.assertEqual(result, "")

    def test_pretty_print_with_format_prefix(self):
        """Test pretty_print_two_columns uses _format_prefix for nested dataclasses."""

        @dataclass
        class WithPrefix:
            _format_prefix: str = "Q_"
            a: int = 7
            bb: str = "baz"

        @dataclass
        class Outer:
            x: int
            y: WithPrefix

        obj = Outer(x=99, y=WithPrefix(a=8, bb="qux"))
        result = pretty_print_two_columns(obj, "")
        # The nested WithPrefix fields should be prefixed with "Q_"
        self.assertIn("Q_a:  8", result)
        self.assertIn("Q_bb: qux", result)
        # The outer field should not be prefixed
        self.assertIn("x:    99", result)
