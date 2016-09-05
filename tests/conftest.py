# coding: utf-8

from __future__ import absolute_import

import json
import os
import random
import time

import mock
import pytest

import ogre.api
import ogre.objects
import ogre.twitter


@pytest.fixture
def api_keys(twitter_keys):
    return {
        'Twitter': twitter_keys,
    }


@pytest.fixture
def interval():
    now = time.time()
    earliest = random.random() * now
    return ogre.objects.Interval(
        earliest=earliest,
        latest=(random.random() * (now - earliest)) + earliest,
    )


@pytest.fixture
def keyword():
    return random.choice(('keyword', '漢字'))


@pytest.fixture
def location():
    return ogre.objects.Location(
        latitude=(random.random() * 180) - 90,
        longitude=(random.random() * 360) - 180,
        radius=random.random() * 10,
        unit=random.choice(('km', 'mi')),
    )


@pytest.fixture
def query(media, quantity, location, interval):
    return ogre.objects.Query(
        media=media,
        keyword=keyword(),
        quantity=quantity,
        location=random.choice((None, location)),
        interval=random.choice((None, interval)),
    )


@pytest.fixture
def query_with_nonempty_interval(query):
    while True:
        nonempty_interval_query = ogre.objects.Query(
            media=query.media,
            keyword=query.keyword,
            quantity=query.quantity,
            location=query.location,
            interval=query.interval or interval(),
        )
        if nonempty_interval_query.interval is not None:
            return nonempty_interval_query


@pytest.fixture
def query_with_nonempty_location(query):
    while True:
        nonempty_location_query = ogre.objects.Query(
            media=query.media,
            keyword=query.keyword,
            quantity=query.quantity,
            location=query.location or location(),
            interval=query.interval,
        )
        if nonempty_location_query.location is not None:
            return nonempty_location_query


@pytest.fixture
def max_queries():
    return random.randint(0, 1000)


@pytest.fixture
def media():
    return random.sample(
        ogre.objects.QUERY_MEDIA,
        random.choice(range(len(ogre.objects.QUERY_MEDIA) + 1)),
    )


@pytest.fixture
def quantity():
    return random.randint(0, 1000)


@pytest.fixture
def retriever(api_keys):
    return ogre.api.OGRe(keys=api_keys)


@pytest.fixture
def sources():
    return ('Twitter',)


@pytest.fixture
def tquery(query):
    return ogre.twitter.twitter_query_from_query(query)


@pytest.fixture
def searchable_query(query):
    while True:
        searchable = ogre.objects.Query(
            media=query.media or media(),
            keyword=query.keyword,
            quantity=query.quantity or quantity(),
            location=query.location,
            interval=query.interval,
        )
        if len(searchable.media) > 0 and searchable.quantity > 0:
            return searchable


@pytest.fixture
def searchable_tquery(searchable_query):
    return ogre.twitter.twitter_query_from_query(searchable_query)


@pytest.fixture
def tquery_with_nonempty_media(searchable_tquery):
    while True:
        nonempty_media_tquery = ogre.twitter.TwitterQuery(
            random.sample(
                ogre.twitter.QUERY_MEDIA,
                random.choice(range(1, len(ogre.twitter.QUERY_MEDIA) + 1)),
            ),
            *searchable_tquery[1:]
        )
        if len(nonempty_media_tquery.media) > 0:
            return nonempty_media_tquery


def twitter_search_limits(remaining, reset):
    """Format a Twitter response to a limits request."""
    return {'resources': {'search': {'/search/tweets': {'remaining': remaining, 'reset': reset}}}}


@pytest.fixture
def twitter_keys():
    return ogre.twitter.TwitterKeys('consumer_key', 'access_token')


@pytest.fixture
def twitter_mock():
    twitter = mock.MagicMock()
    twitter().get_application_rate_limit_status.return_value = twitter_search_limits(2, 9876543210)
    with open(
            os.path.join(os.path.dirname(__file__), 'data', 'Twitter-response-example.json')
    ) as tweets:
        twitter().search.return_value = json.load(tweets)
    twitter().search.side_effect = None
    twitter.reset_mock()
    return twitter


@pytest.fixture
def twitter_mock_limited():
    twitter = mock.MagicMock()
    twitter().get_application_rate_limit_status.return_value = twitter_search_limits(0, 9876543210)
    twitter().search.return_value = {'errors': [{'code': 88, 'message': 'Rate limit exceeded'}]}
    twitter().search.side_effect = None
    twitter.reset_mock()
    return twitter


@pytest.fixture
def twitter_mock_complex():
    twitter = mock.MagicMock()
    twitter().get_application_rate_limit_status.return_value = twitter_search_limits(2, 9876543210)
    twitter().search.return_value = {
        'error': 'Sorry, your query is too complex. Please reduce complexity and try again.'
    }
    twitter().search.side_effect = None
    twitter.reset_mock()
    return twitter


@pytest.fixture
def network_mock():  # TODO
    network = mock.MagicMock()
    network.return_value = None
    network.side_effect = lambda _: StringIO('test_image')
    network.reset_mock()
    return network
