"""
OGRe Twitter Interface Tests

:class:`TwitterTest` -- Twitter interface test template

:meth:`TwitterTest.setUp` -- test initialization

:meth:`TwitterTest.test_sanitize_twitter` -- Twitter parameter preparation tests

:meth:`TwitterTest.test_twitter` -- Twitter API query tests
"""

import base64
import copy
import json
import logging
import os
import unittest
from datetime import datetime
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from mock import MagicMock
from twython import TwythonError
from snowflake2time import snowflake
from ogre import OGRe
from ogre.exceptions import OGReError, OGReLimitError
from ogre.Twitter import twitter, sanitize_twitter


def twitter_limits(remaining, reset):
    """Format a Twitter response to a limits request."""
    return {
        "resources": {
            "search": {
                "/search/tweets": {
                    "remaining": remaining,
                    "reset": reset
                }
            }
        }
    }


class TwitterTest(unittest.TestCase):

    """
    Create objects that test the OGRe module.

    :meth:`TwitterTest.setUp` -- retriever and Twython Mock initialization

    :meth:`TwitterTest.test_sanitize_twitter` -- parameter cleansing tests

    :meth:`TwitterTest.test_twitter` -- API access and results-packaging tests


    Test OGRe's access point to the Twitter API.

    These tests should make sure all input is validated correctly,
    and they should make sure that any relevant Twitter data is extracted
    and packaged in GeoJSON format correctly.

    The first two Tweets in the example Twitter response data
    must be geotagged, and the first one must an image entity attached.
    If any other geotagged data is included, this test will fail;
    however, it is a good idea to include non-geotagged Tweets
    to ensure that OGRe omits them in the returned results.
    """

    def setUp(self):

        """
        Prepare to run tests on the Twitter interface.

        Since OGRe requires API keys to run and they cannot be stored
        conveniently, this test module retrieves them from the OS;
        however, to prevent OGRe from actually querying the APIs
        (and subsequently retrieving unpredictable data),
        a MagicMock object is used to do a dependency injection.
        This relieves the need for setting environment variables
        (although they may be necessary in the future).
        Predictable results are stored in the data directory to be read
        during these tests.
        """

        self.log = logging.getLogger(__name__)
        self.log.debug("Initializing a TwitterTest...")

        self.retriever = OGRe(
            keys={
                "Twitter": {
                    "consumer_key": os.environ.get("TWITTER_CONSUMER_KEY"),
                    "access_token": os.environ.get("TWITTER_ACCESS_TOKEN")
                }
            }
        )
        with open("ogre/test/data/Twitter-response-example.json") as tweets:
            self.tweets = json.load(tweets)
        depleted_tweets = copy.deepcopy(self.tweets)
        depleted_tweets["search_metadata"].pop("next_results", None)
        limit_normal = twitter_limits(2, 1234567890)
        dependency_injections = {
            "regular": {
                "api": {
                    "limit": limit_normal,
                    "return": copy.deepcopy(self.tweets),
                    "effect": None
                },
                "network": {
                    "return": None,
                    "effect": lambda _: StringIO("test_image")
                }
            },
            "limited": {
                "api": {
                    "limit": twitter_limits(0, 1234567890),
                    "return": {
                        "errors": [
                            {
                                "code": 88,
                                "message": "Rate limit exceeded"
                            }
                        ]
                    },
                    "effect": None
                },
                "network": {
                    "return": None,
                    "effect": Exception()
                }
            },
            "imitate": {
                "api": {
                    "limit": limit_normal,
                    "return": None,
                    "effect": TwythonError("TwythonError")
                },
                "network": {
                    "return": None,
                    "effect": Exception()
                }
            },
            "complex": {
                "api": {
                    "limit": limit_normal,
                    "return": {
                        "error": "Sorry, your query is too complex." +
                                 " Please reduce complexity and try again."
                    },
                    "effect": None
                },
                "network": {
                    "return": None,
                    "effect": Exception()
                }
            },
            "deplete": {
                "api": {
                    "limit": twitter_limits(1, 1234567890),
                    "return": copy.deepcopy(depleted_tweets),
                    "effect": None
                },
                "network": {
                    "return": StringIO("test_image"),
                    "effect": None
                }
            }
        }

        self.injectors = {
            "api": {},
            "network": {}
        }
        for name, dependencies in dependency_injections.items():
            api = MagicMock()
            api().get_application_rate_limit_status.return_value =\
                dependencies["api"]["limit"]
            api().search.return_value = dependencies["api"]["return"]
            api().search.side_effect = dependencies["api"]["effect"]
            api.reset_mock()
            self.injectors["api"][name] = api
            network = MagicMock()
            network.return_value = dependencies["network"]["return"]
            network.side_effect = dependencies["network"]["effect"]
            network.reset_mock()
            self.injectors["network"][name] = network

    def test_sanitize_twitter(self):

        """
        Test the Twitter interface parameter sanitizer.

        These tests should verify that malformed or invalid data is detected
        before being sent to Twitter. They should also test that valid data is
        formatted correctly for use by Twython.
        """

        self.log.debug("Testing the Twitter sanitizer...")

        with self.assertRaises(ValueError):
            sanitize_twitter(keys={})
        with self.assertRaises(ValueError):
            sanitize_twitter(keys={"invalid": None})
        with self.assertRaises(ValueError):
            sanitize_twitter(keys={"consumer_key": None})
        with self.assertRaises(ValueError):
            sanitize_twitter(keys={"consumer_key": "key", "invalid": None})
        with self.assertRaises(ValueError):
            sanitize_twitter(
                keys={
                    "consumer_key": "key",
                    "access_token": None
                }
            )
        with self.assertRaises(ValueError):
            sanitize_twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ]
            )
        with self.assertRaises(ValueError):
            sanitize_twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                location=(2, 1, 0, "km")
            )

        self.assertEqual(
            sanitize_twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                media=("text",),
                keyword="test"
            ),
            (
                self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                ("text",),
                "test -pic.twitter.com",
                15,
                None,
                (None, None)
            )
        )
        self.assertEqual(
            sanitize_twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                media=("image",),
                keyword="test"
            ),
            (
                self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                ("image",),
                "test pic.twitter.com",
                15,
                None,
                (None, None)
            )
        )
        self.assertEqual(
            sanitize_twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                location=(0, 1, 2, "km")
            ),
            (
                self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                ("image", "text"),
                "",
                15,
                "0.0,1.0,2.0km",
                (None, None)
            )
        )
        self.assertEqual(
            sanitize_twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                keyword="test",
                interval=(0, 1)
            ),
            (
                self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                ("image", "text"),
                "test",
                15,
                None,
                (-5405765689543753728, -5405765685349449728)
            )
        )

    def test_empty_media(self):
        """Requesting no media returns empty without accessing the Twitter API."""
        self.log.debug("Testing empty media...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        self.assertEqual(
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                media=(),
                keyword="test",
                api=api,
                network=network
            ),
            []
        )
        self.assertEqual(0, api.call_count)
        self.assertEqual(0, api().get_application_rate_limit_status.call_count)
        self.assertEqual(0, api().search.call_count)
        self.assertEqual(0, network.call_count)

    def test_zero_quantity(self):
        """Requesting < 1 result returns empty without accessing the Twitter API."""
        self.log.debug("Testing zero quantity...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        self.assertEqual(
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                keyword="test",
                quantity=0,
                api=api,
                network=network
            ),
            []
        )
        self.assertEqual(0, api.call_count)
        self.assertEqual(0, api().get_application_rate_limit_status.call_count)
        self.assertEqual(0, api().search.call_count)
        self.assertEqual(0, network.call_count)

    def test_zero_query_limit(self):
        """Allowing < 1 query returns empty without accessing the Twitter API."""
        self.log.debug("Testing zero query limit...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        self.assertEqual(
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                keyword="test",
                query_limit=0,
                test=True,
                test_message="Quantity Fail-Fast",
                api=api,
                network=network
            ),
            []
        )
        self.assertEqual(0, api.call_count)
        self.assertEqual(0, api().get_application_rate_limit_status.call_count)
        self.assertEqual(0, api().search.call_count)
        self.assertEqual(0, network.call_count)

    def test_api_invocation(self):
        """The constructor is called appropriately once per request."""
        self.log.debug("Testing API invocation...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        twitter(
            keys=self.retriever.keychain[
                self.retriever.keyring["twitter"]
            ],
            media=("image", "text"),
            keyword="test",
            quantity=2,
            location=(4, 3, 2, "km"),
            interval=(1, 0),
            api=api,
            network=network
        )
        api.assert_called_once_with(
            self.retriever.keychain[
                self.retriever.keyring["twitter"]
            ]["consumer_key"],
            access_token=self.retriever.keychain[
                self.retriever.keyring["twitter"]
            ]["access_token"]
        )

    def test_rate_limit_retrieval(self):
        """The rate limit is retrieved once per request."""
        self.log.debug("Testing rate limit retrieval...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        twitter(
            keys=self.retriever.keychain[
                self.retriever.keyring["twitter"]
            ],
            media=("image", "text"),
            keyword="test",
            quantity=2,
            location=(4, 3, 2, "km"),
            interval=(1, 0),
            api=api,
            network=network
        )
        api().get_application_rate_limit_status.assert_called_once_with()

    def test_api_iteration_invocation(self):
        """The API is queried once per iteration."""
        self.log.debug("Testing appropriate API use and HTTPS by default...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        twitter(
            keys=self.retriever.keychain[
                self.retriever.keyring["twitter"]
            ],
            media=("image", "text"),
            keyword="test",
            quantity=2,
            location=(4, 3, 2, "km"),
            interval=(1, 0),
            api=api,
            network=network
        )
        api().search.assert_called_once_with(
            q="test",
            count=2,
            geocode="4.0,3.0,2.0km",
            since_id=-5405765689543753728,
            max_id=-5405765685349449728
        )

    def test_default_https(self):
        """HTTPS is used by default to retrieve images."""
        self.log.debug("Testing HTTPS by default...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        twitter(
            keys=self.retriever.keychain[
                self.retriever.keyring["twitter"]
            ],
            media=("image", "text"),
            keyword="test",
            quantity=2,
            location=(4, 3, 2, "km"),
            interval=(1, 0),
            api=api,
            network=network
        )
        network.assert_called_once_with(
            self.tweets["statuses"][0]
            ["entities"]["media"][0]["media_url_https"]
        )

    def test_rate_limit_obedience(self):
        """The rate limit is obeyed appropriately."""
        self.log.debug("Testing rate limit obedience...")
        api = self.injectors["api"]["limited"]
        network = self.injectors["network"]["limited"]
        self.assertEqual(
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                keyword="test",
                api=api,
                network=network
            ),
            []
        )
        self.assertEqual(1, api.call_count)
        self.assertEqual(1, api().get_application_rate_limit_status.call_count)
        self.assertEqual(0, api().search.call_count)
        self.assertEqual(0, network.call_count)

    def test_hard_failure(self):
        """Failing hard raises exceptions instead of returning empty."""
        self.log.debug("Testing hard failure...")
        api = self.injectors["api"]["limited"]
        network = self.injectors["network"]["limited"]
        with self.assertRaises(OGReLimitError):
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                keyword="test",
                fail_hard=True,
                api=api,
                network=network
            )
        self.assertEqual(1, api.call_count)
        self.assertEqual(1, api().get_application_rate_limit_status.call_count)
        self.assertEqual(0, api().search.call_count)
        self.assertEqual(0, network.call_count)

    def test_TwythonError_relay(self):  # pylint: disable=invalid-name
        """TwythonErrors are relayed correctly."""
        self.log.debug("Testing TwythonError relay...")
        api = self.injectors["api"]["imitate"]
        network = self.injectors["network"]["imitate"]
        with self.assertRaises(TwythonError):
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                keyword="test",
                api=api,
                network=network
            )
        self.assertEqual(1, api.call_count)
        self.assertEqual(1, api().get_application_rate_limit_status.call_count)
        self.assertEqual(1, api().search.call_count)
        self.assertEqual(0, network.call_count)

    def test_empty_response(self):
        """No "statuses" key in Twitter response causes a break."""
        self.log.debug("Testing empty response...")
        api = self.injectors["api"]["complex"]
        network = self.injectors["network"]["complex"]
        self.assertEqual(
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                keyword="test",
                api=api,
                network=network
            ),
            []
        )
        self.assertEqual(1, api.call_count)
        self.assertEqual(1, api().get_application_rate_limit_status.call_count)
        self.assertEqual(1, api().search.call_count)
        self.assertEqual(0, network.call_count)

    def test_empty_response_with_hard_failure(self):  # pylint: disable=invalid-name
        """No "statuses" key in fail_hard Twitter response causes an exception."""
        self.log.debug("Testing empty response with hard failure...")
        api = self.injectors["api"]["complex"]
        network = self.injectors["network"]["complex"]
        with self.assertRaises(OGReError):
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                keyword="test",
                fail_hard=True,
                api=api,
                network=network
            )
        self.assertEqual(1, api.call_count)
        self.assertEqual(1, api().get_application_rate_limit_status.call_count)
        self.assertEqual(1, api().search.call_count)
        self.assertEqual(0, network.call_count)

    def test_filtering_and_page_depletion(self):  # pylint: disable=invalid-name
        """
        Ungeotagged or untimestamped results are omitted.
        "Text" media is returned when requested.
        "Image" media is not returned unless requested.
        No remaining pages causes a break.
        """
        self.log.debug("Testing filtering and page depletion...")
        api = self.injectors["api"]["deplete"]
        network = self.injectors["network"]["deplete"]
        self.assertEqual(
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                media=("text",),
                keyword="test",
                quantity=4,
                location=(0, 1, 2, "km"),
                interval=(3, 4),
                api=api,
                network=network
            ),
            [
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            self.tweets["statuses"][0]["coordinates"]["coordinates"][0],
                            self.tweets["statuses"][0]["coordinates"]["coordinates"][1]
                        ]
                    },
                    "type": "Feature",
                    "properties": {
                        "source": "Twitter",
                        "text": self.tweets["statuses"][0]["text"],
                        "time": datetime.utcfromtimestamp(
                            snowflake.snowflake2utc(
                                self.tweets["statuses"][0]["id"]
                            )
                        ).isoformat()+"Z"
                    }
                },
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            self.tweets["statuses"][1]
                            ["coordinates"]["coordinates"][0],
                            self.tweets["statuses"][1]
                            ["coordinates"]["coordinates"][1]
                        ]
                    },
                    "type": "Feature",
                    "properties": {
                        "source": "Twitter",
                        "text": self.tweets["statuses"][1]["text"],
                        "time": datetime.utcfromtimestamp(
                            snowflake.snowflake2utc(
                                self.tweets["statuses"][1]["id"]
                            )
                        ).isoformat()+"Z"
                    }
                }
            ]
        )
        self.assertEqual(1, api.call_count)
        self.assertEqual(1, api().get_application_rate_limit_status.call_count)
        self.assertEqual(1, api().search.call_count)
        self.assertEqual(0, network.call_count)

    def test_filtering_counting_and_HTTP(self):  # pylint: disable=invalid-name
        """
        "Text" media is returned when not requested.
        "Image" media is returned when requested.
        Remaining results are calculated correctly.
        Setting "secure" kwarg to False causes HTTP retrieval.
        """
        self.log.debug("Testing filtering, counting, and HTTP on demand...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        self.assertEqual(
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                media=("image",),
                keyword="test",
                quantity=1,
                location=(0, 1, 2, "km"),
                interval=(3, 4),
                secure=False,
                api=api,
                network=network
            ),
            [
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            self.tweets["statuses"][0]
                            ["coordinates"]["coordinates"][0],
                            self.tweets["statuses"][0]
                            ["coordinates"]["coordinates"][1]
                        ]
                    },
                    "type": "Feature",
                    "properties": {
                        "source": "Twitter",
                        "text": self.tweets["statuses"][0]["text"],
                        "image": base64.b64encode("test_image".encode('utf-8')),
                        "time": datetime.utcfromtimestamp(
                            snowflake.snowflake2utc(
                                self.tweets["statuses"][0]["id"]
                            )
                        ).isoformat()+"Z"
                    }
                },
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            self.tweets["statuses"][1]
                            ["coordinates"]["coordinates"][0],
                            self.tweets["statuses"][1]
                            ["coordinates"]["coordinates"][1]
                        ]
                    },
                    "type": "Feature",
                    "properties": {
                        "source": "Twitter",
                        "text": self.tweets["statuses"][1]["text"],
                        "time": datetime.utcfromtimestamp(
                            snowflake.snowflake2utc(
                                self.tweets["statuses"][1]["id"]
                            )
                        ).isoformat()+"Z"
                    }
                }
            ]
        )
        self.assertEqual(1, api.call_count)
        self.assertEqual(1, api().get_application_rate_limit_status.call_count)
        self.assertEqual(1, api().search.call_count)
        network.assert_called_once_with(
            self.tweets["statuses"][0]["entities"]["media"][0]["media_url"]
        )

    def test_strict_media_paging_and_duplication(self):  # pylint: disable=invalid-name
        """
        Setting "strict_media" kwarg to True returns only requested media.
        Parameters for paging are computed correctly.
        Paging is not used unless it is needed.
        Duplicates are not filtered.
        """
        self.log.debug("Testing strict media, paging, and duplication...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        self.assertEqual(
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                media=("image",),
                keyword="test",
                quantity=2,
                location=(0, 1, 2, "km"),
                interval=(3, 4),
                strict_media=True,
                api=api,
                network=network
            ),
            [
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            self.tweets["statuses"][0]
                            ["coordinates"]["coordinates"][0],
                            self.tweets["statuses"][0]
                            ["coordinates"]["coordinates"][1]
                        ]
                    },
                    "type": "Feature",
                    "properties": {
                        "source": "Twitter",
                        "image": base64.b64encode("test_image".encode('utf-8')),
                        "time": datetime.utcfromtimestamp(
                            snowflake.snowflake2utc(
                                self.tweets["statuses"][0]["id"]
                            )
                        ).isoformat()+"Z"
                    }
                },
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            self.tweets["statuses"][0]
                            ["coordinates"]["coordinates"][0],
                            self.tweets["statuses"][0]
                            ["coordinates"]["coordinates"][1]
                        ]
                    },
                    "type": "Feature",
                    "properties": {
                        "source": "Twitter",
                        "image": base64.b64encode("test_image".encode('utf-8')),
                        "time": datetime.utcfromtimestamp(
                            snowflake.snowflake2utc(
                                self.tweets["statuses"][0]["id"]
                            )
                        ).isoformat()+"Z"
                    }
                }
            ]
        )
        self.assertEqual(1, api.call_count)
        self.assertEqual(1, api().get_application_rate_limit_status.call_count)
        self.assertEqual(2, api().search.call_count)
        api().search.assert_has_any_call(
            q="test pic.twitter.com",
            count=2,
            geocode="0.0,0.1,2.0km",
            since_id=-5405765676960841728,
            max_id=-5405765672766537728
        )
        api().search.assert_has_any_call(
            q="test pic.twitter.com",
            count=1,
            geocode="0.0,0.1,2.0km",
            since_id=-5405765676960841728,
            max_id=445633721891164159
        )
        self.assertEqual(2, network.call_count)

    def test_return_format(self):
        """Results are packaged correctly."""
        self.log.debug("Testing return format...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        self.assertEqual(
            twitter(
                keys=self.retriever.keychain[
                    self.retriever.keyring["twitter"]
                ],
                media=("image", "text"),
                keyword="test",
                quantity=2,
                location=(0, 1, 2, "km"),
                interval=(3, 4),
                api=api,
                network=network
            ),
            [
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            self.tweets["statuses"][0]
                            ["coordinates"]["coordinates"][0],
                            self.tweets["statuses"][0]
                            ["coordinates"]["coordinates"][1]
                        ]
                    },
                    "type": "Feature",
                    "properties": {
                        "source": "Twitter",
                        "text": self.tweets["statuses"][0]["text"],
                        "image": base64.b64encode("test_image".encode('utf-8')),
                        "time": datetime.utcfromtimestamp(
                            snowflake.snowflake2utc(
                                self.tweets["statuses"][0]["id"]
                            )
                        ).isoformat()+"Z"
                    }
                },
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            self.tweets["statuses"][1]
                            ["coordinates"]["coordinates"][0],
                            self.tweets["statuses"][1]
                            ["coordinates"]["coordinates"][1]
                        ]
                    },
                    "type": "Feature",
                    "properties": {
                        "source": "Twitter",
                        "text": self.tweets["statuses"][1]["text"],
                        "time": datetime.utcfromtimestamp(
                            snowflake.snowflake2utc(
                                self.tweets["statuses"][1]["id"]
                            )
                        ).isoformat()+"Z"
                    }
                }
            ]
        )


if __name__ == "__main__":
    unittest.main()
