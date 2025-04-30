"""Unit tests for the XDG module."""

import os
import platform
import unittest
from unittest import mock

import pytest

from netvelocimeter.utils.xdg import XDGCategory, XDGPath, XDGSystemPaths, _expand_path


class TestExpandPath(unittest.TestCase):
    """Test the _expand_path function."""

    def test_none_input(self):
        """Test that None input returns None."""
        result = _expand_path(None)
        self.assertIsNone(result)

    def test_no_expansion_needed(self):
        """Test that paths without variables remain unchanged."""
        path = "/regular/path/no/variables"
        result = _expand_path(path)
        self.assertEqual(result, path)

    @mock.patch.dict(os.environ, {"TEST_VAR": "/test/value"})
    def test_env_var_expansion_posix(self):
        """Test expansion of POSIX-style environment variables."""
        path = "$TEST_VAR/subdir"
        expected = "/test/value/subdir"
        result = _expand_path(path)
        self.assertEqual(result, expected)

        path = "${TEST_VAR}/subdir"
        result = _expand_path(path)
        self.assertEqual(result, expected)

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    @mock.patch.dict(os.environ, {"TEST_VAR": "/test/value"})
    def test_env_var_expansion_windows(self):
        """Test expansion of Windows-style environment variables."""
        path = "%TEST_VAR%\\subdir"
        expected = "/test/value\\subdir"  # Note: backslashes preserved
        result = _expand_path(path)
        self.assertEqual(result, expected)

    @mock.patch("os.path.expanduser")
    def test_home_expansion(self, mock_expanduser):
        """Test expansion of ~ for home directory."""
        mock_expanduser.return_value = "/home/testuser/subdir"

        path = "~/subdir"
        expected = "/home/testuser/subdir"
        result = _expand_path(path)

        self.assertEqual(result, expected)
        mock_expanduser.assert_called_once_with(path)

    @mock.patch.dict(os.environ, {"TEST_VAR": "test/value"})
    @mock.patch("os.path.expanduser")
    def test_combined_expansion(self, mock_expanduser):
        """Test combination of environment variables and user directory."""
        # Set up the mock to handle the expansion of home directory
        mock_expanduser.side_effect = lambda p: p.replace("~", "/home/testuser")

        # Path with both ~ and environment variable
        path = "~/subdir/$TEST_VAR/another"

        # Expected: First environment variables get expanded by expandvars
        # Then expanduser handles the tilde - our mock simulates the final result
        expected = "/home/testuser/subdir/test/value/another"

        result = _expand_path(path)
        self.assertEqual(result, expected)

        # Verify that expanduser was called with the env vars already expanded
        mock_expanduser.assert_called_once_with("~/subdir/test/value/another")


class TestXDGPath(unittest.TestCase):
    """Test the XDGPath class."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        path = XDGPath()
        self.assertIsNone(path.envvar)
        self.assertIsNone(path.default)

    def test_init_with_values(self):
        """Test initialization with provided values."""
        path = XDGPath(envvar="TEST_VAR", default="/default/path")
        self.assertEqual(path.envvar, "TEST_VAR")
        self.assertEqual(path.default, "/default/path")

    @mock.patch.dict(os.environ, {"TEST_VAR": "/env/var/path"})
    def test_resolve_path_env_var(self):
        """Test resolving path from environment variable."""
        path = XDGPath(envvar="TEST_VAR", default="/default/path")
        result = path.resolve_path()
        self.assertEqual(result, "/env/var/path")

    def test_resolve_path_missing_envvar_having_default(self):
        """Test resolving path using default when environment variable not set."""
        path = XDGPath(default="/default/path")
        result = path.resolve_path()
        self.assertEqual(result, "/default/path")

    @mock.patch.dict(os.environ, {"TEST_VAR": "/env/var/path"})
    def test_resolve_path_having_envvar_no_default(self):
        """Test resolving path using environment variable when default not set."""
        path = XDGPath(envvar="TEST_VAR")
        result = path.resolve_path()
        self.assertEqual(result, "/env/var/path")

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_resolve_path_default(self):
        """Test resolving path using default when environment variable not set."""
        path = XDGPath(envvar="TEST_VAR", default="/default/path")
        result = path.resolve_path()
        self.assertEqual(result, "/default/path")

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_resolve_path_none(self):
        """Test resolving path when both env var and default are None."""
        path = XDGPath()
        result = path.resolve_path()
        self.assertIsNone(result)


class TestXDGSystemPaths(unittest.TestCase):
    """Test the XDGSystemPaths class."""

    def setUp(self):
        """Set up test fixtures."""
        self.windows_path = XDGPath(envvar="WIN_VAR", default="C:\\default\\win")
        self.posix_path = XDGPath(envvar="POSIX_VAR", default="/default/posix")
        self.system_paths = XDGSystemPaths(windows=self.windows_path, posix=self.posix_path)

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.system_paths.windows, self.windows_path)
        self.assertEqual(self.system_paths.posix, self.posix_path)

    @mock.patch("platform.system", return_value="Windows")
    def test_resolve_path_windows(self, mock_system):
        """Test resolving path on Windows platform."""
        # Create a real XDGSystemPaths object with test paths
        windows_path = XDGPath(default="C:\\test\\windows\\path")
        posix_path = XDGPath(default="/test/posix/path")
        system_paths = XDGSystemPaths(windows=windows_path, posix=posix_path)

        # Call the method under test
        result = system_paths.resolve_path()

        # We should get the Windows path since we mocked platform.system() to return "Windows"
        # This tests actual behavior, not implementation details
        self.assertEqual(result, "C:\\test\\windows\\path")

    @mock.patch("platform.system", return_value="Linux")
    def test_resolve_path_posix(self, mock_system):
        """Test resolving path on POSIX platform."""
        # Create a real XDGSystemPaths object with test paths
        windows_path = XDGPath(default="C:\\test\\windows\\path")
        posix_path = XDGPath(default="/test/posix/path")
        system_paths = XDGSystemPaths(windows=windows_path, posix=posix_path)

        # Call the method under test
        result = system_paths.resolve_path()

        # We should get the POSIX path since we mocked platform.system() to return "Linux"
        # This tests actual behavior, not implementation details
        self.assertEqual(result, "/test/posix/path")


class TestXDGCategory(unittest.TestCase):
    """Test the XDGCategory enum."""

    def test_enum_values(self):
        """Test that all expected categories exist."""
        categories = [
            XDGCategory.DATA,
            XDGCategory.CONFIG,
            XDGCategory.STATE,
            XDGCategory.BIN,
            XDGCategory.CACHE,
            XDGCategory.RUNTIME,
        ]
        self.assertEqual(len(categories), len(XDGCategory))

    def test_value_types(self):
        """Test that all category values are XDGSystemPaths."""
        for category in XDGCategory:
            self.assertIsInstance(category.value, XDGSystemPaths)
            self.assertIsInstance(category.value.windows, XDGPath)
            self.assertIsInstance(category.value.posix, XDGPath)

    @mock.patch.object(XDGSystemPaths, "resolve_path")
    def test_resolve_path_valid(self, mock_resolve):
        """Test resolving a valid absolute path."""
        # Set up the mock to return a valid absolute path
        mock_resolve.return_value = "/absolute/path"

        result = XDGCategory.DATA.resolve_path()

        self.assertEqual(result, "/absolute/path")
        mock_resolve.assert_called_once()

    @mock.patch.object(XDGSystemPaths, "resolve_path")
    def test_resolve_path_none(self, mock_resolve):
        """Test resolving path when None is returned."""
        # Set up the mock to return None
        mock_resolve.return_value = None

        with self.assertRaises(ValueError) as context:
            XDGCategory.DATA.resolve_path()

        self.assertIn("Could not resolve base path", str(context.exception))
        mock_resolve.assert_called_once()

    @mock.patch.object(XDGSystemPaths, "resolve_path")
    def test_resolve_path_relative(self, mock_resolve):
        """Test resolving path when a relative path is returned."""
        # Set up the mock to return a relative path
        mock_resolve.return_value = "relative/path"

        with self.assertRaises(ValueError) as context:
            XDGCategory.DATA.resolve_path()

        self.assertIn("Could not resolve base path", str(context.exception))
        mock_resolve.assert_called_once()

    @mock.patch.object(XDGCategory, "resolve_path")
    def test_resolve_app_path(self, mock_resolve_path):
        """Test resolving application path."""
        # Set up the mock to return a valid absolute path
        mock_resolve_path.return_value = "/absolute/path"

        result = XDGCategory.DATA.resolve_app_path("myapp")

        self.assertEqual(result, os.path.join("/absolute/path", "myapp"))
        mock_resolve_path.assert_called_once()


class TestXDGIntegration(unittest.TestCase):
    """Integration tests for the XDG module."""

    @mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "/custom/config"})
    @mock.patch("platform.system", return_value="Linux")
    def test_posix_env_var(self, mock_system):
        """Test resolving POSIX path from environment variable."""
        result = XDGCategory.CONFIG.resolve_path()
        self.assertEqual(result, "/custom/config")

    @mock.patch.dict(os.environ, {"HOME": "/home/testuser"})
    @mock.patch("platform.system", return_value="Linux")
    def test_posix_env_var_default(self, mock_system):
        """Test resolving POSIX path from default."""
        result = XDGCategory.CONFIG.resolve_path()
        self.assertEqual(result, "/home/testuser/.config")

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch("platform.system", return_value="Linux")
    @mock.patch("os.path.expandvars")
    def test_posix_default(self, mock_expandvars, mock_system):
        """Test resolving POSIX path from default."""
        # Set up the mocks for path expansion
        mock_expandvars.side_effect = lambda p: p.replace("${HOME}", "/home/testuser")
        result = XDGCategory.CONFIG.resolve_path()
        self.assertEqual(result, "/home/testuser/.config")

    @mock.patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"})
    @mock.patch("platform.system", return_value="Windows")
    def test_windows_env_var(self, mock_system):
        """Test resolving Windows path from environment variable."""
        result = XDGCategory.CONFIG.resolve_path()
        self.assertEqual(result, "C:\\Users\\Test\\AppData\\Roaming")

    @mock.patch.dict(os.environ, {"USERPROFILE": "C:\\Users\\Test"}, clear=True)
    @mock.patch("platform.system", return_value="Windows")
    def test_windows_env_var_default(self, mock_system):
        """Test resolving Windows path from default."""
        result = XDGCategory.CONFIG.resolve_path()
        self.assertEqual(result, "C:\\Users\\Test\\AppData\\Roaming")

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch("platform.system", return_value="Windows")
    @mock.patch("os.path.expanduser")
    def test_windows_default(self, mock_expanduser, mock_system):
        """Test resolving Windows path from default."""
        # Set up the mocks for path expansion
        mock_expanduser.side_effect = lambda p: p.replace("~", "\\home\\testuser")
        result = XDGCategory.CONFIG.resolve_path()
        self.assertEqual(result, "\\home\\testuser\\AppData\\Roaming")

    @mock.patch.dict(os.environ, {"LOCALAPPDATA": "C:\\Users\\Test\\AppData\\Local"}, clear=True)
    @mock.patch("platform.system", return_value="Windows")
    def test_windows_nested_vars(self, mock_system):
        """Test resolving Windows path with nested environment variables."""
        # The CACHE category uses ${LOCALAPPDATA}\Temp as default
        result = XDGCategory.CACHE.resolve_path()
        self.assertEqual(result, "C:\\Users\\Test\\AppData\\Local\\Temp")

    def test_app_path_usage(self):
        """Test typical usage of resolve_app_path."""
        # This test may need adjustments based on the running environment
        path = XDGCategory.CONFIG.resolve_app_path("netvelocimeter")
        self.assertTrue(os.path.isabs(path))
        self.assertTrue(path.endswith("netvelocimeter"))
