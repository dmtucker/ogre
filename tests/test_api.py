from __future__ import absolute_import

import gjtk.validate
import pytest

import ogre.twitter


def test_ogre_fetch(retriever, query, twitter_mock):
    assert gjtk.validate.is_feature_collection(
        retriever.fetch(['twitter'], *query, _api=twitter_mock),
    )


def test_ogre_fetch_media_empty(retriever, sources):
    assert retriever.fetch(sources=sources, media=()) == {
        'type': 'FeatureCollection',
        'features': [],
    }


def test_ogre_fetch_quantity_zero(retriever, sources):
    assert retriever.fetch(sources=sources, quantity=0) == {
        'type': 'FeatureCollection',
        'features': [],
    }


def test_ogre_fetch_sources(retriever):
    with pytest.raises(ValueError):
        retriever.fetch('invalid')


def test_ogre_fetch_sources_empty(retriever):
    assert retriever.fetch(()) == {
        'type': 'FeatureCollection',
        'features': [],
    }


def test_ogre_fetch_twitter(retriever, query, twitter_mock):
    assert retriever.fetch(('Twitter',), *query, _api=twitter_mock) == \
        ogre.twitter.fetch(query, retriever.keys['twitter'], _api=twitter_mock)
