# coding: utf-8

"""Tests for ogre.twitter"""

from __future__ import absolute_import

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

import gjtk
import mock
import pytest
import twython

import ogre.exceptions
import ogre.objects
import ogre.twitter


def test_fetch(query, twitter_mock, twitter_keys):
    """ogre.twitter.fetch returns a GeoJSON FeatureCollection."""
    assert gjtk.validate.is_feature_collection(
        ogre.twitter.fetch(query, twitter_keys, _api=twitter_mock),
    )


def test_fetch_complex(tquery_with_nonempty_media, twitter_mock_complex, twitter_keys):
    """No 'statuses' key in a Twitter response causes an exception."""
    with pytest.raises(ogre.exceptions.OGReQueryError):
        ogre.twitter.fetch(tquery_with_nonempty_media[:5], twitter_keys, _api=twitter_mock_complex)
    assert twitter_mock_complex().search.call_count == 1


def test_fetch_get_application_rate_limit_status(query, twitter_mock, twitter_keys, max_queries):
    """The rate limit is never retrieved more than once per request."""
    ogre.twitter.fetch(query, twitter_keys, max_queries=max_queries, _api=twitter_mock)
    assert twitter_mock().get_application_rate_limit_status.call_count < 2


def test_fetch_limited(query, twitter_mock_limited, twitter_keys):
    """The rate limit is obeyed appropriately."""
    assert ogre.twitter.fetch(query, twitter_keys, _api=twitter_mock_limited) == {
        'type': 'FeatureCollection',
        'features': [],
    }
    assert twitter_mock_limited().search.call_count == 0


def test_fetch_max_queries(query, twitter_mock, twitter_keys, max_queries):
    """max_queries is obeyed appropriately."""
    ogre.twitter.fetch(query, twitter_keys, max_queries=max_queries, _api=twitter_mock)
    assert twitter_mock().search.call_count <= max_queries


def test_fetch_media_empty(query, twitter_mock, twitter_keys):
    """Requesting no media returns empty without accessing the API."""
    assert ogre.twitter.fetch(
        ogre.objects.Query(
            media=(),
            keyword=query.keyword,
            quantity=query.quantity,
            location=query.location,
            interval=query.interval,
        ),
        twitter_keys,
        _api=twitter_mock,
    ) == {'type': 'FeatureCollection', 'features': []}
    assert twitter_mock().get_application_rate_limit_status.call_count == 0
    assert twitter_mock().search.call_count == 0


def test_fetch_quantity_zero(query, twitter_mock, twitter_keys):
    """Requesting 0 results returns empty without accessing the API."""
    assert ogre.twitter.fetch(
        ogre.objects.Query(
            media=query.media,
            keyword=query.keyword,
            quantity=0,
            location=query.location,
            interval=query.interval,
        ),
        twitter_keys,
        _api=twitter_mock,
    ) == {'type': 'FeatureCollection', 'features': []}
    assert twitter_mock().get_application_rate_limit_status.call_count == 0
    assert twitter_mock().search.call_count == 0


def test_validate_twitter_keys_iterable():
    with pytest.raises(TypeError):
        ogre.twitter.validate_twitter_keys(0)


def test_twitter_query_from_query(query):
    assert ogre.twitter.validate_twitter_query(ogre.twitter.twitter_query_from_query(query)) is None


'''
"""
def test_twitter_query_from_query(query):
    assert ogre.twitter.twitter_query_from_query(query)
    with self.assertRaises(ValueError):
        ogre.twitter.twitter_query_from_query(ogre.
            location=(2, 1, 0, "km")
        )

    self.assertEqual(
        sanitize_twitter(
            keys=self.retriever.keys["twitter"],
            media=("text",),
            keyword="test"
        ),
        (
            self.retriever.keys["twitter"],
            ("text",),
            "test -pic.twitter.com",
            15,
            None,
            (None, None)
        )
    )
    self.assertEqual(
        sanitize_twitter(
            keys=self.retriever.keys["twitter"],
            media=("image",),
            keyword="test"
        ),
        (
            self.retriever.keys["twitter"],
            ("image",),
            "test pic.twitter.com",
            15,
            None,
            (None, None)
        )
    )
    self.assertEqual(
        sanitize_twitter(
            keys=self.retriever.keys["twitter"],
            location=(0, 1, 2, "km")
        ),
        (
            self.retriever.keys["twitter"],
            ("image", "text"),
            "",
            15,
            "0.0,1.0,2.0km",
            (None, None)
        )
    )
    self.assertEqual(
        sanitize_twitter(
            keys=self.retriever.keys["twitter"],
            keyword="test",
            interval=(0, 1)
        ),
        (
            self.retriever.keys["twitter"],
            ("image", "text"),
            "test",
            15,
            None,
            (-5405765689543753728, -5405765685349449728)
        )
    )
"""











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

        self.default_query = ogre.objects.Query(
            media=('image', 'text'),
            keyword='',
            quantity=15,
            location=None,
            interval=None,
        )

        self.retriever = ogre.api.OGRe(
            keys={
                "Twitter": ogre.twitter.TwitterKeys(
                    consumer_key=os.environ.get("TWITTER_CONSUMER_KEY"),
                    access_token=os.environ.get("TWITTER_ACCESS_TOKEN"),
                ),
            }
        )
        with open(
                os.path.join(os.path.dirname(__file__), 'data', 'Twitter-response-example.json')
        ) as tweets:
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
                    "effect": twython.TwythonError("TwythonError")
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
            api = mock.MagicMock()
            api().get_application_rate_limit_status.return_value =\
                dependencies["api"]["limit"]
            api().search.return_value = dependencies["api"]["return"]
            api().search.side_effect = dependencies["api"]["effect"]
            api.reset_mock()
            self.injectors["api"][name] = api
            network = mock.MagicMock()
            network.return_value = dependencies["network"]["return"]
            network.side_effect = dependencies["network"]["effect"]
            network.reset_mock()
            self.injectors["network"][name] = network

    def test_default_https(self):
        """HTTPS is used by default to retrieve images."""
        self.log.debug("Testing HTTPS by default...")
        api = self.injectors["api"]["regular"]
        network = self.injectors["network"]["regular"]
        ogre.twitter.fetch(
            keys=self.retriever.keys["twitter"],
            media=("image", "text"),
            keyword="test",
            quantity=2,
            location=(4, 3, 2, "km"),
            interval=(1, 0),
            _api=api,
            network=network
        )
        network.assert_called_once_with(
            self.tweets["statuses"][0]
            ["entities"]["media"][0]["media_url_https"]
        )

    def test_filtering_and_page_depletion(self):
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
            ogre.twitter.fetch(
                keys=self.retriever.keys["twitter"],
                media=("text",),
                keyword="test",
                quantity=4,
                location=(0, 1, 2, "km"),
                interval=(3, 4),
                _api=api,
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
                            ogre.twitter.timestamp_from_snowflake_id(
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
                            ogre.twitter.timestamp_from_snowflake_id(
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

    def test_filtering_counting_and_HTTP(self):
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
            ogre.twitter.fetch(
                keys=self.retriever.keys["twitter"],
                media=("image",),
                keyword="test",
                quantity=1,
                location=(0, 1, 2, "km"),
                interval=(3, 4),
                secure=False,
                _api=api,
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
                            ogre.twitter.timestamp_from_snowflake_id(
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
                            ogre.twitter.timestamp_from_snowflake_id(
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
        self.assertEqual(
            set(map(str, ogre.twitter.fetch(
                ogre.objects.Query(
                    media=("image",),
                    keyword="test",
                    quantity=2,
                    location=(0, 1, 2, "km"),
                    interval=(3, 4),
                ),
                keys=self.retriever.keys["twitter"],
                strict=True,
                _api=api,
            )['features'])),
            set(map(str, [
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
                            ogre.twitter.timestamp_from_snowflake_id(
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
                            ogre.twitter.timestamp_from_snowflake_id(
                                self.tweets["statuses"][0]["id"]
                            )
                        ).isoformat()+"Z",
                    },
                },
            ])),
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
'''
