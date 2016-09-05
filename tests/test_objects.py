# coding: utf-8

"""Tests for ogre.objects"""

from __future__ import absolute_import

import random
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

import gjtk
import pytest

import ogre.objects


def test_validate_interval(interval):
    assert ogre.objects.validate_interval(interval) is None


def test_validate_interval_tuple(interval):
    assert ogre.objects.validate_interval(tuple(interval)) is None


def test_validate_interval_iterable():
    with pytest.raises(TypeError):
        ogre.objects.validate_interval(0)


def test_validate_interval_earliest_float(interval):
    with pytest.raises(ValueError):
        ogre.objects.validate_interval(ogre.objects.Interval('not a float', interval[1]))


def test_validate_interval_earliest_nonnegative(interval):
    with pytest.raises(AssertionError):
        ogre.objects.validate_interval(ogre.objects.Interval(-0.001 - interval[0], interval[1]))


def test_validate_interval_latest_float(interval):
    with pytest.raises(ValueError):
        ogre.objects.validate_interval(ogre.objects.Interval(interval[0], 'not a float'))


def test_validate_interval_latest_nonnegative(interval):
    with pytest.raises(AssertionError):
        ogre.objects.validate_interval(ogre.objects.Interval(interval[0], -0.001 - interval[1]))


def test_validate_interval_incorrect_order(interval):
    with pytest.raises(AssertionError):
        ogre.objects.validate_interval(ogre.objects.Interval(interval[1], interval[1] - 1))


def test_validate_location(location):
    assert ogre.objects.validate_location(location) is None


def test_validate_location_tuple(location):
    assert ogre.objects.validate_location(tuple(location)) is None


def test_validate_location_iterable():
    with pytest.raises(TypeError):
        ogre.objects.validate_location(0)


def test_validate_location_latitude(location):
    with pytest.raises(AssertionError):
        ogre.objects.validate_location(ogre.objects.Location(
            latitude=random.choice((1, -1)) * ((random.random() * 1000) + 90.001),
            longitude=location.longitude,
            radius=location.radius,
            unit=location.unit,
        ))


def test_validate_location_latitude_float(location):
    with pytest.raises(ValueError):
        ogre.objects.validate_location(ogre.objects.Location(
            latitude='not a float',
            longitude=location.longitude,
            radius=location.radius,
            unit=location.unit,
        ))


def test_validate_location_longitude(location):
    with pytest.raises(AssertionError):
        ogre.objects.validate_location(ogre.objects.Location(
            latitude=location.latitude,
            longitude=random.choice((1, -1)) * ((random.random() * 1000) + 180.001),
            radius=location.radius,
            unit=location.unit,
        ))


def test_validate_location_longitude_float(location):
    with pytest.raises(ValueError):
        ogre.objects.validate_location(ogre.objects.Location(
            latitude=location.latitude,
            longitude='not a float',
            radius=location.radius,
            unit=location.unit,
        ))


def test_validate_location_radius_float(location):
    with pytest.raises(ValueError):
        ogre.objects.validate_location(ogre.objects.Location(
            latitude=location.latitude,
            longitude=location.longitude,
            radius='not a float',
            unit=location.unit,
        ))


def test_validate_location_radius_nonnegative(location):
    with pytest.raises(AssertionError):
        ogre.objects.validate_location(ogre.objects.Location(
            latitude=location.latitude,
            longitude=location.longitude,
            radius=-0.001 - location.radius,
            unit=location.unit,
        ))


def test_validate_location_unit(location):
    with pytest.raises(AssertionError):
        ogre.objects.validate_location(ogre.objects.Location(
            latitude=location.latitude,
            longitude=location.longitude,
            radius=location.radius,
            unit='invalid',
        ))


def test_validate_query(query):
    assert ogre.objects.validate_query(query) is None


def test_validate_query_tuple(query):
    assert ogre.objects.validate_query(tuple(query)) is None


def test_validate_query_iterable():
    with pytest.raises(TypeError):
        ogre.objects.validate_query(0)


def test_validate_query_media(query):
    with pytest.raises(AssertionError):
        ogre.objects.validate_query(ogre.objects.Query(
            media=tuple('invalid'),
            keyword=query.keyword,
            quantity=query.quantity,
            location=query.location,
            interval=query.interval,
        ))


def test_validate_query_quantity_int(query):
    with pytest.raises(ValueError):
        ogre.objects.validate_query(ogre.objects.Query(
            media=query.media,
            keyword=query.keyword,
            quantity='not an int',
            location=query.location,
            interval=query.interval,
        ))


def test_validate_query_quantity_nonnegative(query):
    with pytest.raises(AssertionError):
        ogre.objects.validate_query(ogre.objects.Query(
            media=query.media,
            keyword=query.keyword,
            quantity=-0.001 - query.quantity,
            location=query.location,
            interval=query.interval,
        ))


def test_validate_query_location_None(query):
    assert ogre.objects.validate_query(ogre.objects.Query(
        media=query.media,
        keyword=query.keyword,
        quantity=query.quantity,
        location=None,
        interval=query.interval,
    )) is None


def test_validate_query_interval_None(query):
    assert ogre.objects.validate_query(ogre.objects.Query(
        media=query.media,
        keyword=query.keyword,
        quantity=query.quantity,
        location=query.location,
        interval=None,
    )) is None


def test_query_from_tuple_identity(query):
    assert ogre.objects.query_from_tuple(tuple(query)) == query


def test_query_from_tuple(query):
    assert isinstance(ogre.objects.query_from_tuple(tuple(query)), ogre.objects.Query)


def test_query_from_tuple_location(query_with_nonempty_location):
    assert isinstance(
        ogre.objects.query_from_tuple(tuple(
            ogre.objects.Query(
                media=query_with_nonempty_location.media,
                keyword=query_with_nonempty_location.keyword,
                quantity=query_with_nonempty_location.quantity,
                location=tuple(query_with_nonempty_location.location),
                interval=query_with_nonempty_location.interval,
            ),
        )).location,
        ogre.objects.Location,
    )


def test_query_from_tuple_interval(query_with_nonempty_interval):
    assert isinstance(
        ogre.objects.query_from_tuple(tuple(
            ogre.objects.Query(
                media=query_with_nonempty_interval.media,
                keyword=query_with_nonempty_interval.keyword,
                quantity=query_with_nonempty_interval.quantity,
                location=query_with_nonempty_interval.location,
                interval=tuple(query_with_nonempty_interval.interval),
            ),
        )).interval,
        ogre.objects.Interval,
    )
