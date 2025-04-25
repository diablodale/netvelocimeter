"""Tests for hash utility functions."""

from base64 import urlsafe_b64encode
from hashlib import sha256
import unittest

from netvelocimeter.utils.hash import hash_b64encode


class TestHashFunctions(unittest.TestCase):
    """Test cases for hash utility functions."""

    def test_hash_b64encode_with_string(self):
        """Test hashing a string input."""
        result = hash_b64encode("test")

        # Verify the result is a string
        self.assertIsInstance(result, str)

        # Verify the length is 22 characters
        self.assertEqual(len(result), 22)

        # Verify the result matches the expected hash of "test"
        # First calculate the expected hash manually
        data = "test"
        data_hash = sha256(data.encode("utf-8")).digest()
        expected = urlsafe_b64encode(data_hash).decode("ascii").rstrip("=")[:22]
        self.assertEqual(result, expected)

    def test_hash_b64encode_with_bytes(self):
        """Test hashing a bytes input."""
        result = hash_b64encode(b"test")

        # Calculate expected result
        data_hash = sha256(b"test").digest()
        expected = urlsafe_b64encode(data_hash).decode("ascii").rstrip("=")[:22]
        self.assertEqual(result, expected)

    def test_hash_b64encode_with_invalid_type(self):
        """Test hashing with an invalid input type."""
        with self.assertRaises(ValueError):
            hash_b64encode(123)  # Integer is not valid

        with self.assertRaises(ValueError):
            hash_b64encode(None)  # None is not valid

        with self.assertRaises(ValueError):
            hash_b64encode([1, 2, 3])  # List is not valid

    def test_hash_b64encode_different_inputs(self):
        """Test that different inputs produce different hashes."""
        hash1 = hash_b64encode("test1")
        hash2 = hash_b64encode("test2")
        self.assertNotEqual(hash1, hash2)

    def test_hash_b64encode_same_inputs(self):
        """Test that same inputs produce the same hash."""
        hash1 = hash_b64encode("test")
        hash2 = hash_b64encode("test")
        self.assertEqual(hash1, hash2)

    def test_hash_b64encode_empty_string(self):
        """Test hashing an empty string."""
        result = hash_b64encode("")
        # Calculate expected result
        data_hash = sha256(b"").digest()
        expected = urlsafe_b64encode(data_hash).decode("ascii").rstrip("=")[:22]
        self.assertEqual(result, expected)

    def test_hash_b64encode_empty_bytes(self):
        """Test hashing empty bytes."""
        result = hash_b64encode(b"")
        # Calculate expected result
        data_hash = sha256(b"").digest()
        expected = urlsafe_b64encode(data_hash).decode("ascii").rstrip("=")[:22]
        self.assertEqual(result, expected)

    def test_hash_b64encode_long_input(self):
        """Test hashing a long string."""
        long_string = "a" * 10000
        result = hash_b64encode(long_string)
        # Verify the length is still 22 characters
        self.assertEqual(len(result), 22)

    def test_hash_b64encode_special_chars(self):
        """Test hashing string with special characters."""
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = hash_b64encode(special_chars)
        # Calculate expected result
        data_hash = sha256(special_chars.encode("utf-8")).digest()
        expected = urlsafe_b64encode(data_hash).decode("ascii").rstrip("=")[:22]
        self.assertEqual(result, expected)

    def test_hash_b64encode_url_safety(self):
        """Test that the output doesn't contain URL-unsafe characters."""
        # Test with multiple inputs to improve coverage
        for test_str in ["test", "test/test", "a+b", "hello world"]:
            result = hash_b64encode(test_str)
            # URL-safe base64 should not contain +, / or =
            self.assertNotIn("+", result)
            self.assertNotIn("/", result)
            self.assertNotIn("=", result)

    def test_hash_b64encode_output_length(self):
        """Test that the output is always 22 characters."""
        # Test with multiple inputs of different lengths
        test_strings = ["", "a", "ab", "abc", "abcd", "a" * 100]
        for test_str in test_strings:
            result = hash_b64encode(test_str)
            self.assertEqual(len(result), 22)

    def test_hash_b64encode_unicode(self):
        """Test hashing Unicode strings."""
        # Test with Unicode strings
        unicode_strings = ["🚀", "résumé", "测试", "Ελληνικά"]
        for unicode_str in unicode_strings:
            result = hash_b64encode(unicode_str)
            # Verify result is correct
            data_hash = sha256(unicode_str.encode("utf-8")).digest()
            expected = urlsafe_b64encode(data_hash).decode("ascii").rstrip("=")[:22]
            self.assertEqual(result, expected)
