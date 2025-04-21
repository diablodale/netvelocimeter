"""Tests for terms module."""

import unittest

from netvelocimeter.terms import AcceptanceTracker, LegalTerms, LegalTermsCategory


class TestLegalTerms(unittest.TestCase):
    """Tests for the LegalTerms class."""

    def test_compute_hash(self):
        """Test the compute_hash method."""
        term1 = LegalTerms(text="Test", url="http://example.com", category=LegalTermsCategory.EULA)
        term2 = LegalTerms(text="Test", url="http://example.com", category=LegalTermsCategory.EULA)
        term3 = LegalTerms(text="Diff", url="http://example.com", category=LegalTermsCategory.EULA)

        # Same content should have same hash
        self.assertEqual(term1.compute_hash(), term2.compute_hash())

        # Different content should have different hash
        self.assertNotEqual(term1.compute_hash(), term3.compute_hash())


class TestAcceptanceTracker(unittest.TestCase):
    """Tests for the AcceptanceTracker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = AcceptanceTracker()
        self.eula_term = LegalTerms(text="EULA", category=LegalTermsCategory.EULA)
        self.privacy_term = LegalTerms(text="Privacy", category=LegalTermsCategory.PRIVACY)
        self.terms_term = LegalTerms(text="Service", category=LegalTermsCategory.SERVICE)

    def tearDown(self):
        """Clean up after each test."""
        # Reset the tracker
        self.tracker = None

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
