from __future__ import absolute_import

import collections


Interval = collections.namedtuple('Interval', ('earliest', 'latest'))  # POSIX timestamps


def validate_interval(interval):
    """Ensure Interval invariants."""
    interval = Interval(*interval)
    assert 0 <= float(interval.earliest) <= float(interval.latest)


Location = collections.namedtuple('Location', ('latitude', 'longitude', 'radius', 'unit'))


def validate_location(location):
    """Ensure Location invariants."""
    location = Location(*location)
    assert -90 <= float(location.latitude) <= 90
    assert -180 <= float(location.longitude) <= 180
    assert float(location.radius) > 0
    assert str(location.unit) in ('km', 'mi')


QUERY_FIELDS = ('media', 'keyword', 'quantity', 'location', 'interval')
Query = collections.namedtuple('Query', QUERY_FIELDS)
QUERY_MEDIA = ('image', 'sound', 'text', 'video')


def validate_query(query):
    """Ensure Query invariants."""
    query = Query(*query)
    assert all([False for medium in query.media if medium not in QUERY_MEDIA])
    str(query.keyword)
    assert int(query.quantity) >= 0
    if query.location is not None:
        validate_location(query.location)
    if query.interval is not None:
        validate_interval(query.interval)


def query_from_tuple(query_tuple):
    return Query(
        media=query_tuple[0],
        keyword=query_tuple[1],
        quantity=query_tuple[2],
        location=None if query_tuple[3] is None else Location(*query_tuple[3]),
        interval=None if query_tuple[4] is None else Interval(*query_tuple[4]),
    )
