"""Unit tests for TimeDuration class."""

import unittest

from netvelocimeter.utils.rates import DataRateMbps, Percentage, TimeDuration


class TestTimeDuration(unittest.TestCase):
    """Test cases for TimeDuration formatting."""

    def test_no_format_spec(self):
        """Test formatting TimeDuration without format spec."""
        d = TimeDuration(seconds=2.5)
        # Should default to seconds
        self.assertEqual(format(d), "2500.00 ms")

    def test_seconds_default(self):
        """Test formatting TimeDuration in seconds without suffix."""
        d = TimeDuration(seconds=1.2345)
        # Default is seconds, no suffix
        self.assertEqual(format(d, ".3f"), "1.234")

    def test_seconds_suffix(self):
        """Test formatting TimeDuration with seconds suffix."""
        d = TimeDuration(seconds=2.5)
        self.assertEqual(format(d, ".1fss"), "2.5 s")
        self.assertEqual(format(d, "ss"), "2 s")

    def test_milliseconds(self):
        """Test formatting TimeDuration in milliseconds."""
        d = TimeDuration(seconds=1.2345)
        self.assertEqual(format(d, ".2fms"), "1234.50 ms")
        self.assertEqual(format(d, "ms"), "1234 ms")

    def test_milliseconds_rounding(self):
        """Test formatting TimeDuration in milliseconds with round half to even."""
        d = TimeDuration(seconds=1.2355)
        self.assertEqual(format(d, ".1fms"), "1235.5 ms")
        self.assertEqual(format(d, "ms"), "1236 ms")

    def test_microseconds(self):
        """Test formatting TimeDuration in microseconds."""
        d = TimeDuration(seconds=0.001234)
        self.assertEqual(format(d, ".1fus"), "1234.0 us")
        self.assertEqual(format(d, "us"), "1234 us")

    def test_nanoseconds(self):
        """Test formatting TimeDuration in nanoseconds."""
        # Use a value that is exactly 789 microseconds (not nanoseconds)
        d = TimeDuration(microseconds=789)
        self.assertEqual(format(d, ".2fns"), "789000.00 ns")
        self.assertEqual(format(d, "ns"), "789000 ns")

    def test_zero_duration(self):
        """Test formatting TimeDuration of zero."""
        d = TimeDuration(seconds=0)
        self.assertEqual(format(d, "ms"), "0 ms")
        self.assertEqual(format(d, ".2fss"), "0.00 s")

    def test_negative_duration(self):
        """Test formatting TimeDuration with negative values."""
        d = TimeDuration(seconds=-1.5)
        self.assertEqual(format(d, ".1fms"), "-1500.0 ms")
        self.assertEqual(format(d, "ss"), "-2 s")


class TestPercentage(unittest.TestCase):
    """Test cases for Percentage class."""

    def test_valid_range(self):
        """Test creating Percentage with valid values."""
        self.assertEqual(Percentage(0.0), 0.0)
        self.assertEqual(Percentage(100.0), 100.0)
        self.assertEqual(Percentage(42.5), 42.5)

    def test_format(self):
        """Test formatting Percentage with different format specs."""
        self.assertEqual(format(Percentage(0.0), ".2f"), "0.00 %")
        self.assertEqual(format(Percentage(100.0), ".1f"), "100.0 %")
        self.assertEqual(format(Percentage(42.1234), ".2f"), "42.12 %")
        self.assertEqual(format(Percentage(50), ".0f"), "50 %")


class TestDataRateMbps(unittest.TestCase):
    """Test cases for DataRateMbps class."""

    def test_basic(self):
        """Test creating DataRateMbps with basic values."""
        self.assertEqual(DataRateMbps(0.0), 0.0)
        self.assertEqual(DataRateMbps(123.456), 123.456)

    def test_format(self):
        """Test formatting DataRateMbps with different format specs."""
        self.assertEqual(format(DataRateMbps(0.0), ".2f"), "0.00 Mbps")
        self.assertEqual(format(DataRateMbps(100.0), ".1f"), "100.0 Mbps")
        self.assertEqual(format(DataRateMbps(42.1234), ".2f"), "42.12 Mbps")
        self.assertEqual(format(DataRateMbps(50), ".0f"), "50 Mbps")
