"""Tests for terms module."""

from concurrent.futures import ThreadPoolExecutor, as_completed, wait as futures_wait
import json
import os
import shutil
import tempfile
import threading
from time import sleep
import unittest
from unittest import mock

from netvelocimeter.terms import AcceptanceTracker, LegalTerms, LegalTermsCategory


class TestLegalTerms(unittest.TestCase):
    """Tests for the LegalTerms class."""

    def test_compute_hash(self):
        """Test the unique_id method."""
        term1 = LegalTerms(text="Test", url="http://example.com", category=LegalTermsCategory.EULA)
        term2 = LegalTerms(text="Test", url="http://example.com", category=LegalTermsCategory.EULA)
        term3 = LegalTerms(text="Diff", url="http://example.com", category=LegalTermsCategory.EULA)
        term4 = LegalTerms(
            text="Test", url="http://example.com", category=LegalTermsCategory.PRIVACY
        )

        # Same content should have same hash
        self.assertEqual(term1.unique_id(), term2.unique_id())

        # Different content should have different hash
        self.assertNotEqual(term1.unique_id(), term3.unique_id())
        self.assertNotEqual(term1.unique_id(), term4.unique_id())

    def test_invalid_methodology_version(self):
        """Test invalid methodology version raises ValueError."""
        term = LegalTerms(text="Test", category=LegalTermsCategory.EULA)
        with self.assertRaises(ValueError):
            term.unique_id(methodology_version=2)

    def test_invalid_terms_content(self):
        """Test invalid content raises ValueError."""
        with self.assertRaises(ValueError):
            _ = LegalTerms(category=LegalTermsCategory.EULA)

    def test_invalid_terms_category(self):
        """Test invalid content raises ValueError."""
        with self.assertRaises(ValueError):
            _ = LegalTerms(text="Test", category=None, url="")
        with self.assertRaises(ValueError):
            _ = LegalTerms(category=2, url="https://example.com")


class TestAcceptanceTracker(unittest.TestCase):
    """Tests for the AcceptanceTracker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = AcceptanceTracker(config_root=self.temp_dir)
        self.eula_term = LegalTerms(text="EULA", category=LegalTermsCategory.EULA)
        self.privacy_term = LegalTerms(text="Privacy", category=LegalTermsCategory.PRIVACY)
        self.terms_term = LegalTerms(text="Service", category=LegalTermsCategory.SERVICE)

    def tearDown(self):
        """Clean up after each test."""
        # Reset the tracker
        self.tracker = None
        shutil.rmtree(self.temp_dir)

    def test_is_recorded_single_term(self):
        """Test checking if a single term is recorded."""
        # Initially not recorded
        self.assertFalse(self.tracker.is_recorded(self.eula_term))

        # After recording, it should be recorded
        self.tracker.record(self.eula_term)
        self.assertTrue(self.tracker.is_recorded(self.eula_term))

    def test_is_recorded_collection(self):
        """Test checking if a collection of terms is recorded."""
        collection = [self.eula_term, self.privacy_term]

        # Initially not recorded
        self.assertFalse(self.tracker.is_recorded(collection))

        # After recording one term, collection still not fully recorded
        self.tracker.record(self.eula_term)
        self.assertFalse(self.tracker.is_recorded(collection))

        # After recording all terms, collection should be recorded
        self.tracker.record(self.privacy_term)
        self.assertTrue(self.tracker.is_recorded(collection))

    def test_record_collection(self):
        """Test recording a collection of terms."""
        collection = [self.eula_term, self.privacy_term]

        # Record the collection
        self.tracker.record(collection)

        # Each term should be recorded
        self.assertTrue(self.tracker.is_recorded(self.eula_term))
        self.assertTrue(self.tracker.is_recorded(self.privacy_term))
        self.assertTrue(self.tracker.is_recorded(collection))

    def test_invalid_acceptance_config_root(self):
        """Test invalid acceptance config root raises ValueError."""
        with self.assertRaises(ValueError):
            AcceptanceTracker(config_root="invalid_path")

    def test_invalid_terms_or_collection(self):
        """Test invalid terms or collection raises TypeError."""
        with self.assertRaises(TypeError):
            self.tracker.is_recorded("invalid_type")
        with self.assertRaises(TypeError):
            self.tracker.is_recorded([1, 2, 3])
        with self.assertRaises(TypeError):
            self.tracker.record("invalid_type")
        with self.assertRaises(TypeError):
            self.tracker.record([1, 2, 3])

    def test_two_recordings_by_two_accept_trackers(self):
        """Test if two trackers can record terms independently."""
        # Create a new tracker instance
        new_tracker = AcceptanceTracker(config_root=self.temp_dir)

        # Record terms in both trackers
        self.tracker.record(self.eula_term)
        new_tracker.record(self.privacy_term)

        # Check if both trackers have recorded the terms
        self.assertTrue(self.tracker.is_recorded(self.eula_term))
        self.assertTrue(new_tracker.is_recorded(self.privacy_term))


class TestAcceptanceTrackerThreading(unittest.TestCase):
    """Test the AcceptanceTracker class with concurrent threads."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = AcceptanceTracker(config_root=self.temp_dir)

        # Create test terms
        self.eula_terms = LegalTerms(
            text="Test EULA for threading",
            url="https://example.com/eula",
            category=LegalTermsCategory.EULA,
        )

        self.terms_of_service = LegalTerms(
            text="Test Terms of Service for threading",
            url="https://example.com/terms",
            category=LegalTermsCategory.SERVICE,
        )

        self.privacy_terms = LegalTerms(
            text="Test Privacy Policy for threading",
            url="https://example.com/privacy",
            category=LegalTermsCategory.PRIVACY,
        )

        # Collection of all terms
        self.all_terms = [self.eula_terms, self.terms_of_service, self.privacy_terms]

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_concurrent_is_recorded(self):
        """Test that is_recorded works correctly with multiple threads."""
        # Record one term first
        self.tracker.record(self.eula_terms)

        # Number of threads to use
        thread_count = 10

        # Results container
        results = []

        def check_recorded():
            # Check if terms are recorded
            results.append(self.tracker.is_recorded(self.eula_terms))
            results.append(not self.tracker.is_recorded(self.terms_of_service))

        # Launch multiple threads to check terms concurrently
        threads = []
        for _ in range(thread_count):
            t = threading.Thread(target=check_recorded)
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify results
        self.assertEqual(len(results), thread_count * 2)
        self.assertTrue(all(r is True for r in results[::2]))  # EULA terms should be recorded
        self.assertTrue(
            all(r is True for r in results[1::2])
        )  # Terms of service should not be recorded

    def test_concurrent_record(self):
        """Test that record works correctly with multiple threads recording the same term."""
        # Number of threads to use
        thread_count = 20

        # Using ThreadPoolExecutor for easier management
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Submit the same recording task multiple times
            futures = [
                executor.submit(self.tracker.record, self.eula_terms) for _ in range(thread_count)
            ]

            # Wait for all tasks to complete
            futures_wait(futures)

        # Verify the term was recorded
        self.assertTrue(self.tracker.is_recorded(self.eula_terms))

        # Check that the file exists and is valid
        file_path = os.path.join(self.temp_dir, *self.eula_terms.unique_id().split("/")) + ".json"
        self.assertTrue(os.path.exists(file_path))

    def test_concurrent_record_different_terms(self):
        """Test multiple threads recording different terms concurrently."""
        results = []

        def record_and_check(terms):
            # Record the terms
            self.tracker.record(terms)
            # Verify it was recorded
            recorded = self.tracker.is_recorded(terms)
            results.append(recorded)
            return recorded

        # Using ThreadPoolExecutor for easier management
        with ThreadPoolExecutor(max_workers=len(self.all_terms)) as executor:
            # Submit different recording tasks
            futures = [executor.submit(record_and_check, term) for term in self.all_terms]

            # Get results
            for future in as_completed(futures):
                self.assertTrue(future.result())

        # All terms should be recorded
        self.assertEqual(len(results), len(self.all_terms))
        self.assertTrue(all(results))
        self.assertTrue(self.tracker.is_recorded(self.all_terms))

    def test_race_condition_handling(self):
        """Test handling of race conditions when recording terms."""
        # Number of threads to use - higher number increases chance of race conditions
        thread_count = 30

        # Track the actual file path that will be used
        terms_id = self.eula_terms.unique_id()
        file_path = self.tracker._acceptance_file_path(terms_id)

        # Create counters to track operations with thread-safe access
        file_stats = {"open_attempts": 0, "exists_checks": 0, "fileexists_exceptions": 0}
        lock = threading.Lock()

        # Original functions to patch
        original_open = open
        original_exists = os.path.exists
        original_json_dump = json.dump

        # Create patched versions to count operations
        def counting_open(*args, **kwargs):
            nonlocal file_stats
            if (
                args
                and args[0] == file_path
                and "x" in (args[1] if len(args) > 1 else kwargs.get("mode", ""))
            ):
                with lock:
                    file_stats["open_attempts"] += 1

                # Allow normal open to proceed, potentially causing FileExistsError
                try:
                    # Call the original open function
                    return original_open(*args, **kwargs)
                except FileExistsError:
                    with lock:
                        file_stats["fileexists_exceptions"] += 1
                    raise
            return original_open(*args, **kwargs)

        def counting_exists(path):
            nonlocal file_stats
            if path == file_path:
                with lock:
                    file_stats["exists_checks"] += 1
            return original_exists(path)

        # Create patched versions of json.dump to delay
        def slow_json_dump(*args, **kwargs):
            # Call the original json.dump function
            original_json_dump(*args, **kwargs)

            # Simulate a delay to increase the chance of race conditions
            sleep(0.1)

        # Apply the patches
        with (
            mock.patch("builtins.open", counting_open),
            mock.patch("os.path.exists", counting_exists),
            mock.patch("json.dump", slow_json_dump),
        ):
            # Run multiple threads to create race conditions
            threads = []
            for _ in range(thread_count):
                t = threading.Thread(target=lambda: self.tracker.record(self.eula_terms))
                threads.append(t)
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join()

        # Verify results
        self.assertTrue(self.tracker.is_recorded(self.eula_terms))

        # With race conditions, we expect:

        # 1. Multiple existence checks - one per thread
        self.assertEqual(file_stats["exists_checks"], thread_count)

        # 2. Multiple open attempts but not all threads should get that far
        # (some will exit early due to is_recorded() check once file exists)
        self.assertGreaterEqual(file_stats["open_attempts"], 1)
        self.assertLessEqual(file_stats["open_attempts"], thread_count)

        # 3. Some FileExistsError exceptions should be caught if race conditions occurred
        # (This is crucial - we want to verify the exception handling works)
        self.assertGreaterEqual(file_stats["fileexists_exceptions"], 1)

        # 4. The file should exist and contain valid JSON
        self.assertTrue(os.path.exists(file_path))
        with original_open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("ts", data)  # Timestamp should be present


class TestLegalTermsRepresentation(unittest.TestCase):
    """Tests for LegalTerms string representation and dictionary conversion."""

    def test_str_with_text_only(self):
        """Test string representation with text only."""
        terms = LegalTerms(
            category=LegalTermsCategory.EULA,
            text="Sample EULA text",
        )
        result = str(terms)

        self.assertIn("category: EULA", result)
        self.assertIn("text: Sample EULA text", result)
        self.assertNotIn("url:", result)

    def test_str_with_url_only(self):
        """Test string representation with URL only."""
        terms = LegalTerms(
            category=LegalTermsCategory.PRIVACY,
            url="https://example.com/privacy",
        )
        result = str(terms)

        self.assertIn("category: PRIVACY", result)
        self.assertIn("url: https://example.com/privacy", result)
        self.assertNotIn("text:", result)

    def test_str_with_both_text_and_url(self):
        """Test string representation with both text and URL."""
        terms = LegalTerms(
            category=LegalTermsCategory.SERVICE,
            text="Service terms content",
            url="https://example.com/terms",
        )
        result = str(terms)

        self.assertIn("category: SERVICE", result)
        self.assertIn("text: Service terms content", result)
        self.assertIn("url: https://example.com/terms", result)

    def test_str_lines_order(self):
        """Test that string representation maintains consistent line order."""
        terms = LegalTerms(
            category=LegalTermsCategory.NDA,
            text="NDA content",
            url="https://example.com/nda",
        )
        result = str(terms).split("\n")

        self.assertEqual(len(result), 3)
        self.assertTrue(result[0].startswith("category:"))
        self.assertTrue(result[1].startswith("text:"))
        self.assertTrue(result[2].startswith("url:"))

    def test_to_dict_with_text_only(self):
        """Test dictionary conversion with text only."""
        terms = LegalTerms(
            category=LegalTermsCategory.EULA,
            text="Sample EULA text",
        )
        result = terms.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["category"], "EULA")
        self.assertEqual(result["text"], "Sample EULA text")
        self.assertIsNone(result["url"])

    def test_to_dict_with_url_only(self):
        """Test dictionary conversion with URL only."""
        terms = LegalTerms(
            category=LegalTermsCategory.PRIVACY,
            url="https://example.com/privacy",
        )
        result = terms.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["category"], "PRIVACY")
        self.assertIsNone(result["text"])
        self.assertEqual(result["url"], "https://example.com/privacy")

    def test_to_dict_with_both_text_and_url(self):
        """Test dictionary conversion with both text and URL."""
        terms = LegalTerms(
            category=LegalTermsCategory.SERVICE,
            text="Service terms content",
            url="https://example.com/terms",
        )
        result = terms.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["category"], "SERVICE")
        self.assertEqual(result["text"], "Service terms content")
        self.assertEqual(result["url"], "https://example.com/terms")

    def test_to_dict_contains_all_required_keys(self):
        """Test that dictionary contains all required keys even when values are None."""
        terms = LegalTerms(
            category=LegalTermsCategory.OTHER,
            text="Other terms",
        )
        result = terms.to_dict()

        self.assertEqual(set(result.keys()), {"category", "text", "url"})

    def test_to_dict_returns_new_dict(self):
        """Test that to_dict returns a new dict each time, not a reference."""
        terms = LegalTerms(
            category=LegalTermsCategory.EULA,
            text="Sample text",
        )
        dict1 = terms.to_dict()
        dict2 = terms.to_dict()

        # Verify they're not the same object
        self.assertIsNot(dict1, dict2)

        # But contain the same data
        self.assertEqual(dict1, dict2)


class TestLegalTermsFromOther(unittest.TestCase):
    """Tests for creating LegalTerms from other formats."""

    def test_from_dict_with_text_only(self):
        """Test from_dict with text only."""
        data = {"category": "eula", "text": "Sample EULA text"}
        terms = LegalTerms.from_dict(data)

        self.assertIsInstance(terms, LegalTerms)
        self.assertEqual(terms.category, LegalTermsCategory.EULA)
        self.assertEqual(terms.text, "Sample EULA text")
        self.assertIsNone(terms.url)

    def test_from_dict_with_url_only(self):
        """Test from_dict with URL only."""
        data = {"category": "privacy", "url": "https://example.com/privacy"}
        terms = LegalTerms.from_dict(data)

        self.assertIsInstance(terms, LegalTerms)
        self.assertEqual(terms.category, LegalTermsCategory.PRIVACY)
        self.assertIsNone(terms.text)
        self.assertEqual(terms.url, "https://example.com/privacy")

    def test_from_dict_with_both_text_and_url(self):
        """Test from_dict with both text and URL."""
        data = {
            "category": "service",
            "text": "Service terms content",
            "url": "https://example.com/terms",
        }
        terms = LegalTerms.from_dict(data)

        self.assertIsInstance(terms, LegalTerms)
        self.assertEqual(terms.category, LegalTermsCategory.SERVICE)
        self.assertEqual(terms.text, "Service terms content")
        self.assertEqual(terms.url, "https://example.com/terms")

    def test_from_dict_missing_category(self):
        """Test from_dict with missing category raises ValueError."""
        data = {"text": "Missing category"}
        with self.assertRaises(KeyError) as context:
            LegalTerms.from_dict(data)

        self.assertIn("category", str(context.exception))

    def test_from_dict_missing_text_and_url(self):
        """Test from_dict with missing text and URL raises ValueError."""
        data = {"category": "other"}
        with self.assertRaises(ValueError) as context:
            LegalTerms.from_dict(data)

        self.assertIn("'text' or 'url' value must be provided", str(context.exception))

    def test_from_dict_invalid_category(self):
        """Test from_dict with invalid category raises ValueError."""
        data = {"category": "invalid_category", "text": "Some text"}
        with self.assertRaises(ValueError) as context:
            LegalTerms.from_dict(data)

        self.assertIn("invalid_category", str(context.exception))

    def test_from_dict_extra_fields(self):
        """Test from_dict ignores extra fields."""
        data = {
            "category": "nda",
            "text": "NDA content",
            "extra_field": "Should be ignored",
            "another_field": 123,
        }
        terms = LegalTerms.from_dict(data)

        self.assertEqual(terms.category, LegalTermsCategory.NDA)
        self.assertEqual(terms.text, "NDA content")
        self.assertFalse(hasattr(terms, "extra_field"))
