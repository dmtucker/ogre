# coding: utf-8

"""Tests for ogre.cli"""

from __future__ import absolute_import

import pytest

import ogre.cli


def test___main__():
    """Test python -m functionality."""
    with pytest.raises(SystemExit) as excinfo:
        import ogre.__main__  # pylint: disable=redefined-outer-name, unused-variable
    assert excinfo.value != 0


def test_empty():
    """Test invocation with no arguments."""
    with pytest.raises(SystemExit) as excinfo:
        ogre.cli.main()
    assert excinfo.value != 0
