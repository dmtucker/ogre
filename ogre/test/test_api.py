"""
OGRe Query Handler Tests

:class:`OGReConstructorTest` -- retriever constructor test template

:meth:`OGReConstructorTest.test___init__` -- retriever creation tests

:class:`OGReTest` -- query handler test template

:meth:`OGReTest.setUp` -- query handler test preparation

:meth:`OGReTest.test_fetch` -- query handler tests
"""

import json
import logging
import os
import unittest
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO  # pylint: disable=import-error
from mock import MagicMock
from ogre import OGRe
from ogre.Twitter import twitter


class OGReConstructorTest(unittest.TestCase):

    """
    Create objects that test the OGRe constructor.

    A separate class is required here because the constructor is used in the
    setUp method of future TestCase classes.

    :meth:`test___init__` -- retriever creation and key-handling tests
    """

    def setUp(self):
        """Prepare to test the OGRe constructor."""
        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing an OGReConstructorTest...")

    def test___init__(self):

        """
        Test key handling during OGRe construction.

        These tests should ensure that only valid keys are accepted
        and that the keyring is properly created.
        """

        self.log.debug("Testing the OGRe constructor...")

        with self.assertRaises(AttributeError):
            OGRe(keys={0: None})
        with self.assertRaises(ValueError):
            OGRe(keys={"invalid": None})
        with self.assertRaises(AttributeError):
            OGRe(keys={"Twitter": None, 0: None})
        with self.assertRaises(ValueError):
            OGRe(keys={"Twitter": None, "invalid": None})

        retriever = OGRe(
            keys={
                "Twitter": {
                    "consumer_key": "key",
                    "access_token": "token",
                }
            }
        )

        self.assertEqual(
            retriever.keyring,
            {"twitter": "Twitter"}
        )
        self.assertEqual(
            retriever.keychain,
            {
                "Twitter": {
                    "consumer_key": "key",
                    "access_token": "token",
                }
            }
        )


class OGReTest(unittest.TestCase):

    """
    Create objects that test the OGRe module.

    :meth:`setUp` -- query handler test preparation (always runs first)

    :meth:`test_fetch` -- query handling and packaging tests
    """

    def setUp(self):

        """
        Prepare to run tests on OGRe.

        Since OGRe requires API keys to run and they cannot be stored
        conveniently, this test module retrieves them from the environment;
        however, to prevent OGRe from actually querying the APIs
        (and subsequently retrieving unpredictable data),
        a MagicMock object is used to do a dependency injection.
        This relieves the need for setting environment variables
        (although they may be necessary in the future).
        Predictable results are stored in the data directory to be read
        during these tests.
        The network is also injected to prevent testing from depending on
        and internet connection or sources being up.
        """

        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing an OGReTest...")

        self.retriever = OGRe(
            keys={
                "Twitter": {
                    "consumer_key": os.environ.get("TWITTER_CONSUMER_KEY"),
                    "access_token": os.environ.get("TWITTER_ACCESS_TOKEN")
                }
            }
        )

        self.api = MagicMock()
        self.api().get_application_rate_limit_status.return_value = {
            "resources": {
                "search": {
                    "/search/tweets": {
                        "remaining": 2,
                        "reset": 1234567890
                    }
                }
            }
        }
        with open("ogre/test/data/Twitter-response-example.json") as tweets:
            self.api().search.return_value = json.load(tweets)
        self.api.reset_mock()
        self.network = MagicMock()
        self.network.side_effect = lambda _: StringIO(u"test_image")
        self.network.reset_mock()

    def test_fetch(self):

        """
        Test the main entry point to OGRe.

        These tests should ensure that the retrieved results are packaged
        in a GeoJSON FeatureCollection object properly.
        They should also verify that empty requests fail fast
        (e.g. quantity < 1 or media == []).
        """

        self.log.debug("Testing the main entry point to OGRe...")

        with self.assertRaises(ValueError):
            self.retriever.fetch(("invalid",))
        with self.assertRaises(ValueError):
            self.retriever.fetch(("Twitter", "invalid"))

        self.assertEqual(
            self.retriever.fetch(sources=()),
            {
                "type": "FeatureCollection",
                "features": []
            }
        )
        self.assertEqual(
            self.retriever.fetch(sources=("Twitter",), media=()),
            {
                "type": "FeatureCollection",
                "features": []
            }
        )
        self.assertEqual(
            self.retriever.fetch(sources=("Twitter",), quantity=0),
            {
                "type": "FeatureCollection",
                "features": []
            }
        )

        self.api.reset_mock()
        self.network.reset_mock()
        control = {
            "type": "FeatureCollection",
            "features": twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                media=("image", "text"),
                keyword="test",
                quantity=2,
                location=(0, 1, 2, "km"),
                interval=(3, 4),
                test=True,
                test_message="GeoJSON FeatureCollection Packaging (Control)",
                api=self.api,
                network=self.network
            )
        }
        self.api.reset_mock()
        self.network.reset_mock()
        self.assertEqual(
            control,
            self.retriever.fetch(
                sources=("Twitter",),
                media=("image", "text"),
                keyword="test",
                quantity=2,
                location=(0, 1, 2, "km"),
                interval=(3, 4),
                test=True,
                test_message="GeoJSON FeatureCollection Packaging",
                api=self.api,
                network=self.network
            )
        )


if __name__ == "__main__":
    unittest.main()
