"""OGRe Twitter Interface"""

from __future__ import absolute_import

import base64
import collections
import datetime
import logging
import uuid
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from twython import Twython

import ogre.exceptions
import ogre.objects


LOG = logging.getLogger(__name__)


TwitterKeys = collections.namedtuple('TwitterKeys', ['consumer_key', 'access_token'])


def validate_twitter_keys(keys):
    keys = TwitterKeys(*keys)
    str(keys.access_token)
    str(keys.consumer_key)


def twitter_geocode_from_location(location):
    """Create a string of the form "latitude,longitude,radiusunit"."""
    return '{0},{1},{2}{3}'.format(*location)


def snowflake_id(timestamp):
    """Create a Snowflake ID from a POSIX timestamp."""
    return (int(round(timestamp * 1000)) - 1288834974657) << 22


def timestamp_from_snowflake_id(snowflake_id):
    """Create a Snowflake ID from a POSIX timestamp."""
    return ((snowflake_id >> 22) + 1288834974657) / 1000.0


TwitterQuery = collections.namedtuple(
    'TwitterQuery',
    ogre.objects.QUERY_FIELDS + ('geocode', 'since_id', 'max_id'),
)
QUERY_MEDIA = ('image', 'text')


def validate_twitter_query(tquery):
    """Ensure TwitterQuery invariants."""
    tquery = TwitterQuery(*tquery)
    ogre.objects.validate_query(tquery[:5])
    assert all(medium in QUERY_MEDIA for medium in set(tquery.media))
    str(tquery.keyword)
    if tquery.location is not None:
        assert tquery.geocode == twitter_geocode_from_location(tquery.location)
    if tquery.interval is not None:
        assert tquery.since_id == snowflake_id(tquery.interval.earliest)
        assert tquery.max_id == snowflake_id(tquery.interval.latest)


def twitter_query_from_query(query):
    """Produce a santized copy of the provided query."""

    query = ogre.objects.query_from_tuple(query)

    media = tuple([medium for medium in set(query.media) if medium in QUERY_MEDIA])

    keyword = query.keyword
    if len(media) == 1:
        keyword += {
            'image': ' pic.twitter.com',
            'text': ' -pic.twitter.com',
        }.get(media[0])
    keyword = keyword.strip()

    geocode = None
    if query.location is not None and query.location.radius > 0:
        geocode = twitter_geocode_from_location(query.location)

    if keyword in ('', '-pic.twitter.com') and geocode is None:
        raise ValueError('Specify either a keyword or a location.')

    return TwitterQuery(
        media=media,
        keyword=keyword,
        quantity=query.quantity,
        location=query.location,
        interval=query.interval,
        geocode=geocode,
        since_id=None if query.interval is None else snowflake_id(query.interval.earliest),
        max_id=None if query.interval is None else snowflake_id(query.interval.latest),
    )


def search_limits(_api=Twython):
    """Fetch search limits from Twitter."""
    limits = _api.get_application_rate_limit_status()
    try:
        remaining = int(limits['resources']['search']['/search/tweets']['remaining'])
        reset = int(limits['resources']['search']['/search/tweets']['reset'])
        LOG.info('%d queries remain.', remaining)
    except KeyError:
        message = 'Limits are not available.'
        LOG.critical(message)
        raise ogre.exceptions.OGReLimitError(message, source=__name__)
    if remaining < 1:
        LOG.warning('The query limit has been reached.')
    return remaining, reset


def geojson_from_tweet(tweet, media=('image', 'text'), strict=False, _api=urlopen):
    """Produce a GeoJSON Feature from a Tweet (as returned from the Twitter API)."""
    feature = {
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [
                tweet['coordinates']['coordinates'][0],
                tweet['coordinates']['coordinates'][1],
            ],
        },
        'properties': {
            'source': __name__,
            'time': datetime.datetime.utcfromtimestamp(
                timestamp_from_snowflake_id(tweet['id']),
            ).isoformat() + 'Z',
            'original': tweet,
        },
    }
    if 'text' in media or not strict:
        if tweet.get('text') is not None:
            feature['properties']['text'] = tweet['text']
    if 'image' in media or not strict:
        for entity in tweet.get('entities', {}).get('media', ()):
            if entity.get('type', '').lower() == 'photo':
                media_url = entity.get('media_url_https', entity.get('media_url'))
                if media_url is not None:
                    feature['properties']['image'] = base64.b64encode(_api(media_url).read())
                    break
    return feature


def fetch(
        query,  # ogre.objects.Query
        keys,  # TwitterKeys
        strict=False,
        max_queries=450,  # Twitter allows 450 queries every 15 minutes.
        _api=Twython,  # This is a dependency injection for testing.
):

    tquery = twitter_query_from_query(query)
    validate_twitter_keys(keys)
    api = _api(keys.consumer_key, access_token=keys.access_token)
    qid = str(uuid.uuid4())[:8]
    LOG.info('[%s] %s Query', qid, __name__.capitalize())
    LOG.debug('[%s] query=%s, tquery=%s', qid, query, tquery)

    feature_collection = {
        'type': 'FeatureCollection',
        'features': [],
    }

    if len(tquery.media) < 1 or tquery.quantity < 1 or max_queries < 1:
        LOG.info('[%s] No results were requested.', qid)
        return feature_collection

    query_count = 0
    query_limit = min(search_limits(_api=api)[0], max_queries)
    max_id = tquery.max_id
    remaining = tquery.quantity
    while remaining > 0:
        if query_count >= query_limit:
            LOG.warning('[%s] The query limit has been reached.', qid)
            break
        response = api.search(
            q=tquery.keyword,
            count=min(remaining, 100),  # Twitter accepts a max count of 100.
            geocode=tquery.geocode,
            since_id=tquery.since_id,
            max_id=max_id,
        )
        query_count += 1
        if response.get('statuses') is None:
            message = 'The request is too complex.'
            LOG.warning('[%s] %s', qid, message)
            raise ogre.exceptions.OGReQueryError(message, source=__name__)
        feature_collection['features'].extend([
            geojson_from_tweet(tweet, media=tquery.media, strict=strict)
            for tweet in [  # Tweets must be geotagged and timestamped.
                status for status in response['statuses']
                if status.get('coordinates') is not None and status.get('id') is not None
            ]
        ])
        remaining = tquery.quantity - len(feature_collection['features'])
        if response.get('search_metadata', {}).get('next_results') is None:
            LOG.info('[%s] All available results have been retrieved.', qid)
            break
        max_id = int(response['search_metadata']['next_results'].split('max_id=')[1].split('&')[0])
    LOG.debug(
        '[%s] %d queries (of the %d limit) produced %d results (of the %d requested).',
        qid,
        query_count,
        query_limit,
        len(feature_collection['features']),
        tquery.quantity,
    )

    return feature_collection
