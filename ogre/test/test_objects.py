"""
OGRe Parameter Validator Tests

:class:`ValidationTest` -- parameter validator test template

:meth:`ValidationTest.test_validate` -- error detection tests

:meth:`ValidationTest.test_sanitize` -- data cleansing verification tests
"""

import logging
import unittest
from ogre.objects import validate, sanitize


class ValidationTest(unittest.TestCase):

    """
    Create objects that test the OGRe validation module.

    :meth:`test_validate` -- tests for detecting input errors

    :meth:`test_sanitize` -- tests of parameter format preparation
    """

    def setUp(self):
        """Prepare to run tests on the OGRe validation module."""
        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing a ValidationTest...")

    def test_validate(self):

        """
        Test input validation.

        These tests should make sure all input is validated correctly.
        """

        self.log.debug("Testing the OGRe validator...")

        with self.assertRaises(AttributeError):
            validate(media=(0,))
        with self.assertRaises(AttributeError):
            validate(media=("text", 0))
        with self.assertRaises(ValueError):
            validate(media=("invalid",))
        with self.assertRaises(ValueError):
            validate(media=("text", "invalid"))
        with self.assertRaises(ValueError):
            validate(quantity=-1)
        with self.assertRaises(ValueError):
            validate(location=(1, 2, 3))
        with self.assertRaises(ValueError):
            validate(location=(1, 2, 3, 4, 5))
        with self.assertRaises(ValueError):
            validate(location=("malformed", 0, 0, "km"))
        with self.assertRaises(ValueError):
            validate(location=(-100, 0, 0, "km"))
        with self.assertRaises(ValueError):
            validate(location=(100, 0, 0, "km"))
        with self.assertRaises(ValueError):
            validate(location=(0, "malformed", 0, "km"))
        with self.assertRaises(ValueError):
            validate(location=(0, -200, 0, "km"))
        with self.assertRaises(ValueError):
            validate(location=(0, 200, 0, "km"))
        with self.assertRaises(ValueError):
            validate(location=(0, 0, "malformed", "km"))
        with self.assertRaises(ValueError):
            validate(location=(0, 0, -1, "km"))
        with self.assertRaises(AttributeError):
            validate(location=(0, 0, 0, 0))
        with self.assertRaises(ValueError):
            validate(location=(0, 0, 0, "invalid"))
        with self.assertRaises(ValueError):
            validate(interval=("malformed",))
        with self.assertRaises(ValueError):
            validate(interval=(0, "malformed"))
        with self.assertRaises(ValueError):
            validate(interval=(-1, 1))
        with self.assertRaises(ValueError):
            validate(interval=(1, -1))

    def test_sanitize(self):

        """
        Test input sanitation.

        These tests should make sure all input is sanitized correctly.
        """

        self.log.debug("Testing the OGRe sanitizer...")

        self.assertEqual(
            sanitize(media=()),
            ((), "", 15, None, None)
        )
        self.assertEqual(
            sanitize(media=("text", "text")),
            (("text",), "", 15, None, None)
        )
        self.assertEqual(
            sanitize(location=("0", 0, 0, "km")),
            (("image", "sound", "text", "video"), "", 15, (0, 0, 0, "km"), None)
        )
        self.assertEqual(
            sanitize(location=(0, "0", 0, "km")),
            (("image", "sound", "text", "video"), "", 15, (0, 0, 0, "km"), None)
        )
        self.assertEqual(
            sanitize(location=(0, 0, "0", "km")),
            (("image", "sound", "text", "video"), "", 15, (0, 0, 0, "km"), None)
        )
        self.assertEqual(
            sanitize(interval=("0", 0)),
            (("image", "sound", "text", "video"), "", 15, None, (0, 0))
        )
        self.assertEqual(
            sanitize(interval=(0, "0")),
            (("image", "sound", "text", "video"), "", 15, None, (0, 0))
        )
        self.assertEqual(
            sanitize(interval=(1, 0)),
            (("image", "sound", "text", "video"), "", 15, None, (0, 1))
        )


if __name__ == "__main__":
    unittest.main()
