"""
OGRe Twitter Interface

:func:`twitter` : method for fetching data from Twitter
"""

import base64
import hashlib
import logging
import sys
import time
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen  # pylint: disable=import-error
from datetime import datetime
from twython import Twython
from ogre.validation import sanitize
from ogre.exceptions import OGReError, OGReLimitError
from snowflake2time.snowflake import snowflake2utc, utc2snowflake


def sanitize_twitter(
        keys,
        media=('image', 'text'),
        keyword='',
        quantity=15,
        location=None,
        interval=None,
):  # pylint: disable=too-many-arguments,too-many-locals

    """
    Validate and prepare parameters for use in Twitter data retrieval.

    .. seealso:: :meth:`ogre.validation.validate` describes the format each
                 parameter must have.

    :type keys: dict
    :param keys: Specify Twitter API keys.
                 Twitter **requires** a "consumer_key" and "access_token".

    :type media: tuple
    :param media: Specify content mediums to make lowercase and deduplicate.
                  "image" and "text" are supported mediums.

    :type keyword: str
    :param keyword: Specify search criteria to incorporate
                    the requested media in.

    :type quantity: int
    :param quantity: Specify a quota of results.

    :type location: tuple
    :param location: Specify a location to format as a Twitter geocode
                     ("<latitude>,<longitude>,<radius><unit>").

    :type interval: tuple
    :param interval: Specify earliest and latest moments to convert to
                     Twitter Snowflake IDs.

    :raises: ValueError

    :rtype: tuple
    :returns: Each passed parameter is returned (in order) in the proper format.
    """

    clean_keys = {}
    for key, value in keys.items():
        key = key.lower()
        if key not in ('consumer_key', 'access_token'):
            raise ValueError('Valid Twitter keys are "consumer_key" and "access_token".')
        if not value:
            raise ValueError('Twitter API keys are required.')
        clean_keys[key] = value
    if 'consumer_key' not in clean_keys.keys() or 'access_token' not in clean_keys.keys():
        raise ValueError('Twitter API keys must include a "consumer_key" and "access_token".')

    clean_media, clean_keyword, clean_quantity, clean_location, clean_interval = \
        sanitize(
            media=media,
            keyword=keyword,
            quantity=quantity,
            location=location,
            interval=interval,
        )

    kinds = []
    if clean_media is not None:
        for clean_medium in clean_media:
            if clean_medium in ('image', 'text'):
                kinds.append(clean_medium)
    kinds = tuple(kinds)  # pylint: disable=redefined-variable-type

    keywords = clean_keyword
    if kinds == ('image',):
        keywords += '  pic.twitter.com'
    elif kinds == ('text',):
        keywords += ' -pic.twitter.com'
    keywords = keywords.strip()

    geocode = None
    if location is not None and clean_location[2] > 0:
        geocode = \
            str(clean_location[0]) + ',' +\
            str(clean_location[1]) + ',' +\
            str(clean_location[2]) + clean_location[3]

    period_id = (None, None)
    if interval is not None:
        period_id = (
            utc2snowflake(clean_interval[0]),
            utc2snowflake(clean_interval[1]),
        )

    if keywords in ('', '-pic.twitter.com') and geocode is None:
        raise ValueError('Specify either a keyword or a location.')

    return (
        clean_keys,
        kinds,
        keywords,
        clean_quantity,
        geocode,
        period_id,
    )


def twitter(
        keys,
        media=('image', 'text'),
        keyword='',
        quantity=15,
        location=None,
        interval=None,
        **kwargs
):  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements

    """
    Fetch Tweets from the Twitter API.

    .. seealso:: :meth:`sanitize_twitter` describes more about
                 the format each parameter must have.

    :type keys: dict
    :param keys: Specify an API key and access token.

    :type media: tuple
    :param media: Specify content mediums to fetch.
                  "text" or "image" are supported mediums.

    :type keyword: str
    :param keyword: Specify search criteria.
                    "Queries can be limited due to complexity."
                    If this happens, no results will be returned.
                    To avoid this, follow Twitter Best Practices including
                    the following:
                    "Limit your searches to 10 keywords and operators."

    :type quantity: int
    :param quantity: Specify a quota of results to fetch.
                     Twitter will return 15 results by default,
                     and up to 100 can be requested in a single query.
                     If a number larger than 100 is specified,
                     the retriever will make multiple queries in an attempt
                     to satisfy the requested `quantity`,
                     but this is done on a best effort basis.
                     Whether the specified number is returned or
                     not depends on Twitter.

    :type location: tuple
    :param location: Specify a place (latitude, longitude, radius, unit)
                     to search.
                     Since OGRe only returns geotagged results,
                     the larger the specified radius,
                     the fewer results will be returned.
                     This is because of the way Twitter satisfies
                     geocoded queries.
                     It uses so-called "fuzzy matching logic" to deduce the
                     location of Tweets posted publicly without location data.
                     OGRe filters these out.

    :type interval: tuple
    :param interval: Specify a period of time (earliest, latest) to search.
                     "The Search API is not complete index of all Tweets,
                     but instead an index of recent Tweets."
                     Twitter's definition of "recent" is rather vague,
                     but when an interval is not specified,
                     "that index includes between 6-9 days of Tweets."

    :type strict_media: bool
    :param strict_media: Specify whether to only return the requested media
                         (defaults to False).
                         Setting this to False helps build caches faster at
                         no additional cost.
                         For instance, since Twitter automatically sends the
                         text of a Tweet back, if `("image",)` is passed for
                         `media`, the text on hand will only be filtered if
                         `strict_media` is True.

    :type secure: bool
    :param secure: Specify whether to prefer HTTPS or not (defaults to True).

    :type test: bool
    :param test: Specify whether a the current request is a trial run.
                 This affects what gets logged and should be accompanied by
                 the next 3 parameters (`test_message`, `api`, and `network`).

    :type test_message: str
    :param test_message: Specify a description of the test to log.
                         This is ignored if the `test` parameter is False.

    :type api: callable
    :param api: Specify API access point (for dependency injection).

    :type network: callable
    :param network: Specify a network access point (for dependency injection).

    :raises: OGReError, OGReLimitError, TwythonError

    :rtype: list
    :returns: GeoJSON Feature(s)

    .. seealso:: Visit https://dev.twitter.com/docs/using-search for tips on
                 how to build queries for Twitter using the `keyword` parameter.
                 More information may also be found at
                 https://dev.twitter.com/docs/api/1.1/get/search/tweets.
    """

    keychain, kinds, keywords, remaining, geocode, (since_id, max_id) = \
        sanitize_twitter(
            keys=keys,
            media=media,
            keyword=keyword,
            quantity=quantity,
            location=location,
            interval=interval,
        )

    modifiers = {
        'api': Twython,
        'fail_hard': False,
        'network': urlopen,
        'query_limit': 450,  # Twitter allows 450 queries every 15 minutes.
        'secure': True,
        'strict_media': False,
    }
    for modifier in modifiers:
        if kwargs.get(modifier) is not None:
            modifiers[modifier] = kwargs[modifier]

    qid = hashlib.md5(
        ''.join(
            map(str, (time.time(), keywords, remaining, geocode, since_id, max_id, kwargs)),
        ).encode('utf-8'),
    ).hexdigest()

    log = logging.getLogger(__name__)
    log.info(qid + ' Request: Twitter')
    log.debug(
        qid + ' Status:' +
        ' media(' + str(media)+')' +
        ' keyword(' + str(keywords) + ')' +
        ' quantity(' + str(remaining) + ')' +
        ' location(' + str(geocode) + ')' +
        ' interval(' + str(since_id) + ',' + str(max_id) + ')' +
        ' kwargs(' + str(kwargs) + ')',
    )

    if not kinds or remaining < 1 or modifiers['query_limit'] < 1:
        log.info(qid + ' Success: No results were requested.')
        return []

    api = modifiers['api'](keychain['consumer_key'], access_token=keychain['access_token'])

    limits = api.get_application_rate_limit_status()
    try:
        limit = int(limits['resources']['search']['/search/tweets']['remaining'])
        reset = int(limits['resources']['search']['/search/tweets']['reset'])
        if limit < 1:
            message = 'Queries are being limited.'
            log.info(qid + ' Failure: ' + message)
            if modifiers['fail_hard']:
                raise OGReLimitError(source='Twitter', message=message, reset=reset)
        else:
            log.debug(qid + ' Status: ' + str(limit) + ' queries remain.')
        if limit < modifiers['query_limit']:
            modifiers['query_limit'] = limit
    except KeyError:
        log.warning(qid + ' Unobtainable Rate Limit')
    total = remaining

    collection = []
    for query in range(modifiers['query_limit']):  # pylint: disable=too-many-nested-blocks
        count = min(remaining, 100)  # Twitter accepts a max count of 100.
        try:
            results = api.search(
                q=keywords,
                count=count,
                geocode=geocode,
                since_id=since_id,
                max_id=max_id,
            )
        except:
            log.info(
                qid + ' Failure: ' +
                str(query + 1) + ' queries produced ' +
                str(len(collection)) + ' results. ' +
                str(sys.exc_info()[1]),
            )
            raise
        if results.get('statuses') is None:
            message = 'The request is too complex.'
            log.info(
                qid + ' Failure: ' +
                str(query + 1) + ' queries produced ' +
                str(len(collection)) + ' results. ' +
                message,
            )
            if modifiers['fail_hard']:
                raise OGReError(source='Twitter', message=message)
            break
        for tweet in results['statuses']:
            if tweet.get('coordinates') is None or tweet.get('id') is None:
                # Tweets must be geotagged and timestamped.
                continue
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
                    'source': 'Twitter',
                    'time': datetime.utcfromtimestamp(snowflake2utc(tweet['id'])).isoformat() + 'Z',
                },
            }
            if 'text' in kinds:
                if tweet.get('text') is not None:
                    feature['properties']['text'] = tweet['text']
            if 'image' in kinds:
                if not modifiers['strict_media']:
                    if tweet.get('text') is not None:
                        feature['properties']['text'] = tweet['text']
                if tweet.get('entities', {}).get('media') is not None:
                    for entity in tweet['entities']['media']:
                        if entity.get('type') is not None:
                            if entity['type'].lower() == 'photo':
                                media_url = 'media_url_https'
                                if not modifiers['secure']:
                                    media_url = 'media_url'
                                if entity.get(media_url) is not None:
                                    feature['properties']['image'] =\
                                        base64.b64encode(
                                            modifiers['network'](entity[media_url])
                                            .read()
                                            .encode('utf-8')
                                        )
            if len(feature['properties']) > 2:
                collection.append(feature)
        remained = remaining
        remaining = total - len(collection)
        log.debug(qid + ' Status:' + ' 1 query produced ' + str(remained-remaining) + ' results.')
        if remaining <= 0:
            log.info(
                qid + ' Success: ' +
                str(query+1) + ' queries produced ' +
                str(len(collection)) + ' results.',
            )
            break
        if results.get('search_metadata', {}).get('next_results') is None:
            outcome = 'Success' if len(collection) > 0 else 'Failure'
            log.info(
                qid + ' ' + outcome + ': ' +
                str(query+1) + ' queries produced ' +
                str(len(collection)) + ' results. ' +
                'No retrievable results remain.',
            )
            break
        max_id = int(
            results['search_metadata']['next_results']
            .split('max_id=')[1]
            .split('&')[0],
        )
        if query+1 >= modifiers['query_limit']:
            outcome = 'Success' if len(collection) > 0 else 'Failure'
            log.info(
                qid + ' ' + outcome + ': ' +
                str(query+1) + ' queries produced ' +
                str(len(collection)) + ' results. ' +
                'No remaining results are retrievable.',
            )
    return collection
